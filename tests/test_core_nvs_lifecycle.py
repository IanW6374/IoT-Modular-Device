"""Exercise patched native NVS ownership and every frozen-store open path."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import credential_store
from test_core_transport_patch import before_patch
from tools.micropython_patches import apply_core_patches, restore_core_patches

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'firmware/patches/nvs-handle-lifecycle.patch'


class FrozenCredentialHandleTests(unittest.TestCase):
    def setUp(self):
        credential_store._reset_memory_backend()
        self.opened = []
        opened = self.opened

        class TrackedNVS(credential_store._MemoryNVS):
            def __init__(self, namespace):
                self.closed = False
                self.close_count = 0
                opened.append(self)

            def __enter__(self):
                if self.closed:
                    raise OSError('closed handle')
                return self

            def __exit__(self, *exception):
                self.close()

            def close(self):
                if not self.closed:
                    self.closed = True
                    self.close_count += 1

        self.backend = mock.patch.object(credential_store, 'esp32', SimpleNamespace(NVS=TrackedNVS))
        self.backend.start()
        self.addCleanup(self.backend.stop)
        self.addCleanup(credential_store._reset_memory_backend)

    def assert_closed(self):
        self.assertTrue(self.opened)
        self.assertTrue(all(s.closed and s.close_count == 1 for s in self.opened))

    def test_repeated_reads_and_missing_keys_close_without_gc(self):
        for i in range(1000):
            self.assertEqual(credential_store.load(), {})
            self.assertEqual(credential_store._read_network_trial(), {})
            self.assertEqual(credential_store.bootstrap_key(), '')
            self.assertEqual(credential_store.update_verification_key(), b'')
            self.assertFalse(credential_store.factory_reset_pending())
            self.assert_closed()
        self.assertEqual(len(self.opened), 5000)

    def test_successful_save_read_network_trial_and_reset_paths_close(self):
        with mock.patch.object(credential_store, 'validate', side_effect=lambda value, *args: value):
            config = {'schema': credential_store.SCHEMA_VERSION, 'provisioned': False}
            credential_store.save(config)
            self.assertEqual(credential_store.load(), config)
        credential_store._write_network_trial({'version': 1, 'previous': {}, 'candidate_wifi': {}})
        self.assertEqual(credential_store._read_network_trial()['version'], 1)
        credential_store._clear_network_trial()
        credential_store.erase_bootstrap_key()
        credential_store.request_factory_reset('Test-Recovery-Cedar-47!')
        self.assertTrue(credential_store.factory_reset_pending())
        self.assertTrue(credential_store.complete_factory_reset())
        self.assertFalse(credential_store.factory_reset_pending())
        self.assert_closed()

    def test_write_and_commit_errors_close_and_propagate(self):
        for operation in ('set_blob', 'commit', 'set_i32'):
            with (
                mock.patch.object(credential_store, 'validate'),
                mock.patch.object(credential_store._MemoryNVS, operation, side_effect=OSError('injected failure')),
                self.assertRaises(OSError)
            ):
                credential_store.save({'schema': credential_store.SCHEMA_VERSION})
            self.assert_closed()
        with self.assertRaises(RuntimeError):
            credential_store.load(require_provisioned=True)
        self.assert_closed()


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class NativeNvsLifecycleTests(unittest.TestCase):
    def test_actual_native_helpers_constructor_failure_and_double_close(self):
        originals = before_patch(PATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative, source in originals.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            applied = apply_core_patches(root, [PATCH])
            try:
                source = (root / 'ports/esp32/esp32_nvs.c').read_text()
                helpers = '// NVS handles own' + source.split('// NVS handles own', 1)[1].split('// esp32_nvs_print', 1)[0]
                body = re.search(r'    // Get requested nvs namespace\n.*?\n}', source, re.S).group()
                prefix = r'''
                    #include <assert.h>
                    #include <stdbool.h>
                    #include <stddef.h>
                    #include <stdint.h>
                    #include <setjmp.h>
                    typedef void *mp_obj_t;
                    typedef uint32_t nvs_handle_t;
                    typedef struct { nvs_handle_t namespace; } esp32_nvs_obj_t;
                    #define MP_OBJ_TO_PTR(o) (o)
                    #define MP_OBJ_FROM_PTR(o) (o)
                    #define mp_const_none NULL
                    #define NVS_READWRITE 1
                    #define ESP_ERR_NVS_INVALID_HANDLE -100
                    #define MP_DEFINE_CONST_FUN_OBJ_1(name,fn) const int name __attribute__((unused)) = 0
                    #define MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(name,lo,hi,fn) const int name __attribute__((unused)) = 0
                    static int opens, closes, outstanding, alloc_fail, open_fail;
                    static jmp_buf exception;
                    static esp32_nvs_obj_t allocated;
                    static void check_esp_err(int result) { if (result) longjmp(exception, 1); }
                    static const char *mp_obj_str_get_str(mp_obj_t o) { return o; }
                    static void *mock_alloc(void) {
                        if (alloc_fail) longjmp(exception, 1);
                        return &allocated;
                    }
                    #define mp_obj_malloc_with_finaliser(type,kind) mock_alloc()
                    static int nvs_open(const char *name, int mode, nvs_handle_t *out) {
                        assert(name && mode == NVS_READWRITE); ++opens;
                        if (open_fail) return -1;
                        assert(!allocated.namespace); *out = opens; ++outstanding; return 0;
                    }
                    static void nvs_close(nvs_handle_t handle) {
                        assert(handle && !allocated.namespace); ++closes; --outstanding;
                    }
                '''
                suffix = r'''
                    int main(void) {
                        mp_obj_t args[] = { "iotmd_config", NULL, NULL, NULL };
                        for (int i = 0; i < 10000; ++i) {
                            mp_obj_t self = construct(args);
                            args[0] = self;
                            assert(esp32_nvs_enter(self) == self && outstanding == 1);
                            assert(esp32_nvs_exit(4, args) == NULL && outstanding == 0);
                            esp32_nvs_close(self); // Explicit close and finaliser are idempotent.
                            assert(closes == opens);
                            if (setjmp(exception) == 0) {
                                esp32_nvs_enter(self); assert(false);
                            }
                            args[0] = "iotmd_config";
                        }
                        int before = opens;
                        alloc_fail = 1;
                        if (setjmp(exception) == 0) { construct(args); assert(false); }
                        assert(opens == before && outstanding == 0);
                        alloc_fail = 0; open_fail = 1;
                        if (setjmp(exception) == 0) { construct(args); assert(false); }
                        assert(!allocated.namespace && outstanding == 0);
                        esp32_nvs_close(&allocated); // Failed constructor finalisation.
                        assert(closes == before);
                        return 0;
                    }
                '''
                binary = root / 'nvs-test'
                code = prefix + helpers + '\nstatic mp_obj_t construct(mp_obj_t *all_args) {\n' + body + suffix
                compiled = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-x', 'c', '-',
                                           '-o', str(binary)], input=code, text=True, capture_output=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                subprocess.run([str(binary)], check=True, capture_output=True)
                for name in ('close', '__del__', '__enter__', '__exit__'):
                    self.assertIn('MP_QSTR_' + name, source)
            finally:
                restore_core_patches(root, applied)
                for relative, original in originals.items():
                    self.assertEqual((root / relative).read_text(), original)
