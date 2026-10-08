"""Compile the actual patched IDF function and inject DMA allocation failures."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.micropython_patches import apply_core_patches, restore_core_patches

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'firmware/patches/esp-idf-aes-dma-cleanup.patch'
RELATIVE = 'components/mbedtls/port/aes/dma/esp_aes_dma_core.c'


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class CoreAesCleanupTests(unittest.TestCase):
    def test_actual_patch_cleans_partial_allocation_and_preserves_success(self):
        original = (ROOT / 'tests/fixtures/esp_aes_dma_ext_ram.c').read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / RELATIVE
            source.parent.mkdir(parents=True)
            source.write_text(original)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            applied = apply_core_patches(root, [PATCH])
            try:
                prefix = r'''
                    #include <assert.h>
                    #include <stdbool.h>
                    #include <stdint.h>
                    #include <stdlib.h>
                    #include <string.h>
                    #define SOC_CACHE_INTERNAL_MEM_VIA_L1CACHE 0
                    #define MALLOC_CAP_DMA 1
                    #define AES_MAX_CHUNK_WRITE_SIZE 1600
                    #define MIN(a,b) ((a)<(b)?(a):(b))
                    #define ESP_LOGE(...) ((void)0)
                    typedef int esp_aes_context;
                    static int calls, fail_at, outstanding, dma_error;
                    static void *allocated[2];
                    static size_t sizes[2];
                    static void *heap_caps_aligned_alloc(size_t alignment, size_t size, uint32_t caps) {
                        assert(alignment == 1 && caps == MALLOC_CAP_DMA);
                        int index = calls++;
                        if (calls == fail_at) return NULL;
                        allocated[index] = malloc(size);
                        sizes[index] = size;
                        assert(allocated[index]);
                        memset(allocated[index], 0xab, size);
                        ++outstanding;
                        return allocated[index];
                    }
                    static void mbedtls_platform_zeroize(void *buf, size_t size) {
                        memset(buf, 0, size);
                    }
                    static void checked_free(void *ptr) {
                        if (!ptr) return;
                        int index = allocated[0] == ptr ? 0 : 1;
                        assert(allocated[index] == ptr);
                        for (size_t i = 0; i < sizes[index]; ++i)
                            assert(((unsigned char *)ptr)[i] == 0);
                        free(ptr);
                        allocated[index] = NULL;
                        --outstanding;
                    }
                    static int esp_aes_process_dma(esp_aes_context *ctx, const unsigned char *in,
                        unsigned char *out, size_t len, uint8_t *stream) {
                        if (dma_error) return -1;
                        memcpy(out, in, len); // Exercise chunking, not cryptographic correctness.
                        return 0;
                    }
                    #define free checked_free
                '''
                suffix = r'''
                    static void reset(int failure) {
                        assert(outstanding == 0);
                        calls = 0; fail_at = failure; dma_error = 0;
                    }
                    int main(void) {
                        esp_aes_context ctx = 0;
                        unsigned char input[3200], output[3200], stream[16];
                        memset(input, 0x55, sizeof(input));
                        // First allocation fails: nothing to release, output zeroed.
                        reset(1); memset(output, 0x11, sizeof(output));
                        assert(esp_aes_process_dma_ext_ram(&ctx, input, output, sizeof(input),
                            stream, true, true) == -1);
                        assert(outstanding == 0 && calls == 1);
                        for (size_t i = 0; i < sizeof(output); ++i) assert(output[i] == 0);
                        // Second allocation fails: previously leaked the first DMA buffer.
                        reset(2); memset(output, 0x11, sizeof(output));
                        assert(esp_aes_process_dma_ext_ram(&ctx, input, output, sizeof(input),
                            stream, true, true) == -1);
                        assert(outstanding == 0 && calls == 2);
                        for (size_t i = 0; i < sizeof(output); ++i) assert(output[i] == 0);
                        // Repeat failure many times; no cumulative loss.
                        for (int i = 0; i < 1000; ++i) {
                            reset(2);
                            assert(esp_aes_process_dma_ext_ram(&ctx, input, output, 1600,
                                stream, true, true) == -1);
                            assert(outstanding == 0);
                        }
                        // DMA execution failure also frees and scrubs both temporary buffers.
                        reset(0); dma_error = 1;
                        assert(esp_aes_process_dma_ext_ram(&ctx, input, output, sizeof(input),
                            stream, true, true) == -1);
                        assert(outstanding == 0);
                        for (int input_copy = 0; input_copy <= 1; ++input_copy) {
                            for (int output_copy = 0; output_copy <= 1; ++output_copy) {
                                reset(0);
                                assert(esp_aes_process_dma_ext_ram(&ctx, input, output, sizeof(input),
                                    stream, input_copy, output_copy) == 0);
                                assert(outstanding == 0 && !memcmp(input, output, sizeof(input)));
                            }
                        }
                        return 0;
                    }
                '''
                binary = root / 'aes-test'
                command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                           '-Wno-unused-parameter', '-x', 'c', '-', '-o', str(binary)]
                subprocess.run(command, input=prefix + source.read_text() + suffix,
                               text=True, check=True, capture_output=True)
                subprocess.run([str(binary)], check=True, capture_output=True)
                # The same test must fail against unpatched vendor code.
                subprocess.run(command, input=prefix + original + suffix,
                               text=True, check=True, capture_output=True)
                result = subprocess.run([str(binary)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
            finally:
                restore_core_patches(root, applied)
                self.assertEqual(source.read_text(), original)

    def test_pinned_build_applies_and_restores_idf_patch_even_on_failure(self):
        lock = json.loads((ROOT / 'firmware/build-lock.json').read_text())
        self.assertIn(PATCH.name, lock['esp_idf_patches'])
        source = (ROOT / 'tools/build_micropython_firmware.py').read_text()
        self.assertIn('applied_idf_patches = apply_core_patches(esp_idf, [', source)
        self.assertIn('restore_core_patches(esp_idf, applied_idf_patches)', source)
