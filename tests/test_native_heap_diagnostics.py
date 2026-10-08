"""Execute the actual native trace lifecycle against simulated IDF APIs."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'firmware/native'


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class NativeHeapDiagnosticsTests(unittest.TestCase):
    def test_bounded_windows_filtering_overflow_and_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stubs = {
                'sdkconfig.h': '#define CONFIG_HEAP_TRACING_STANDALONE 1\n'
                               '#define CONFIG_HEAP_TRACING_STACK_DEPTH 6\n',
                'esp_heap_caps.h': '''
                    #include <stdint.h>
                    #include <stddef.h>
                    #define MALLOC_CAP_SPIRAM 1
                    #define MALLOC_CAP_8BIT 2
                    #define MALLOC_CAP_INTERNAL 4
                    void *heap_caps_calloc(size_t, size_t, uint32_t);
                    void heap_caps_free(void *);
                    size_t heap_caps_get_free_size(uint32_t);
                ''',
                'esp_memory_utils.h': '''
                    #include <stdint.h>
                    #include <stdbool.h>
                    static inline bool esp_ptr_internal(void *p) {
                        return (uintptr_t)p < 0x10000000;
                    }
                ''',
                'esp_heap_trace.h': '''
                    #include <stdbool.h>
                    #include <stddef.h>
                    #include <stdint.h>
                    #define ESP_OK 0
                    #define HEAP_TRACE_LEAKS 1
                    typedef struct {
                        void *address; size_t size; bool freed;
                        void *alloced_by[6];
                    } heap_trace_record_t;
                    typedef struct {
                        size_t count, high_water_mark, capacity, has_overflowed;
                    } heap_trace_summary_t;
                    int heap_trace_init_standalone(heap_trace_record_t *, size_t);
                    int heap_trace_start(int);
                    int heap_trace_alloc_pause(void);
                    int heap_trace_stop(void);
                    int heap_trace_summary(heap_trace_summary_t *);
                    int heap_trace_get(size_t, heap_trace_record_t *);
                ''',
                'esp_log.h': '''
                    #define ESP_LOG_INFO 3
                    void esp_log_level_set(const char *, int);
                    void capture_log(const char *, const char *, ...);
                    #define ESP_LOGI(tag, ...) capture_log(tag, __VA_ARGS__)
                    #define ESP_LOGE(tag, ...) capture_log(tag, __VA_ARGS__)
                ''',
                'esp_timer.h': '#include <stdint.h>\nint64_t esp_timer_get_time(void);\n',
            }
            for name, content in stubs.items():
                (root / name).write_text(content)
            harness = root / 'test.c'
            harness.write_text(r'''
                #include <assert.h>
                #include <stdarg.h>
                #include <stdio.h>
                #include <stdlib.h>
                #include <string.h>
                #include "esp_heap_caps.h"
                #include "esp_heap_trace.h"
                #include "iotmd_heap_diagnostics.h"
                static uint64_t clock_ms = UINT32_MAX - 1000ULL;
                static int failure, allocations, releases, starts, pauses, stops;
                static bool running, attached;
                static int summary_lines, group_lines, errors;
                int64_t esp_timer_get_time(void) { return clock_ms * 1000; }
                void esp_log_level_set(const char *tag, int level) {
                    assert(!strcmp(tag, "IoT-MD-Heap") && level == 3);
                }
                void capture_log(const char *tag, const char *format, ...) {
                    assert(!strcmp(tag, "IoT-MD-Heap"));
                    char buf[1024]; va_list args;
                    va_start(args, format); vsnprintf(buf, sizeof(buf), format, args); va_end(args);
                    if (strstr(buf, "retained_internal=")) {
                        ++summary_lines;
                        assert(strstr(buf, "retained_internal=42 bytes=736"));
                        assert(strstr(buf, "overflow=1 omitted_count=9 omitted_bytes=144"));
                        assert(strstr(buf, "isr_excluded=1"));
                    }
                    if (strstr(buf, " pcs=")) {
                        if (group_lines % 32 == 0) assert(strstr(buf, "retained=2 bytes=96"));
                        ++group_lines;
                    }
                    errors += strstr(buf, "failed") != NULL;
                }
                void *heap_caps_calloc(size_t count, size_t size, uint32_t caps) {
                    assert(caps == (MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
                    assert(count == 2048); ++allocations;
                    return failure == 1 ? NULL : calloc(count, size);
                }
                void heap_caps_free(void *p) {
                    if (p) { assert(!running && !attached); ++releases; free(p); }
                }
                size_t heap_caps_get_free_size(uint32_t caps) { return 100000; }
                int heap_trace_init_standalone(heap_trace_record_t *p, size_t count) {
                    assert(!running); attached = p != NULL;
                    assert(p ? count == 2048 : count == 0); return 0;
                }
                int heap_trace_start(int mode) {
                    assert(attached && mode == HEAP_TRACE_LEAKS); ++starts;
                    if (failure == 2) return -1;
                    running = true; return 0;
                }
                int heap_trace_alloc_pause(void) {
                    assert(running); ++pauses; return failure == 3 ? -1 : 0;
                }
                int heap_trace_stop(void) {
                    assert(running); ++stops;
                    if (failure == 4) return -1;
                    running = false; return 0;
                }
                int heap_trace_summary(heap_trace_summary_t *s) {
                    assert(!running);
                    *s = (heap_trace_summary_t){.count=45, .high_water_mark=55,
                        .capacity=2048, .has_overflowed=1}; return 0;
                }
                int heap_trace_get(size_t index, heap_trace_record_t *r) {
                    assert(!running && index < 45); memset(r, 0, sizeof(*r));
                    r->address = (void *)(uintptr_t)(1000 + index);
                    r->size = index == 0 ? 32 : index == 1 ? 64 : 16;
                    for (int i = 0; i < 6; ++i)
                        r->alloced_by[i] = (void *)(uintptr_t)(100 + (index < 2 ? 0 : index) + i);
                    if (index == 2) r->address = (void *)0x10000000;
                    if (index == 3) r->freed = true;
                    if (index == 4) r->address = NULL;
                    return 0;
                }
                int main(int argc, char **argv) {
                    failure = argc > 1 ? atoi(argv[1]) : 0;
                    iotmd_heap_diagnostics_poll(); // Warm up; no allocations.
                    clock_ms += 89999; iotmd_heap_diagnostics_poll(); assert(!allocations);
                    for (int i = 0; i < 3; ++i) {
                        clock_ms += i ? 600000 : 1; iotmd_heap_diagnostics_poll();
                        clock_ms += 119999; iotmd_heap_diagnostics_poll();
                        if (!failure) assert(pauses == i);
                        clock_ms += 1; iotmd_heap_diagnostics_poll();
                        clock_ms += 44999; iotmd_heap_diagnostics_poll();
                        if (!failure) assert(summary_lines == i);
                        clock_ms += 1; iotmd_heap_diagnostics_poll();
                    }
                    if (failure == 1) assert(allocations == 1 && releases == 0 && starts == 0);
                    else if (failure == 2) assert(allocations == 1 && releases == 1 && starts == 1);
                    else if (failure == 3) assert(releases == 1 && pauses == 1 && stops == 1);
                    else if (failure == 4) assert(releases == 0 && running && attached);
                    else {
                        assert(allocations == 1 && releases == 1 && starts == 3 && pauses == 3 && stops == 3);
                        assert(summary_lines == 3 && group_lines == 96 && !running && !attached);
                    }
                    if (failure) assert(errors == 1 && !summary_lines);
                    // Finished/error states never restart themselves.
                    clock_ms += 3600000; iotmd_heap_diagnostics_poll();
                    assert(allocations == 1);
                    return 0;
                }
            ''')
            binary = root / 'heap-test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-I', str(root), '-I', str(NATIVE),
                            str(NATIVE / 'iotmd_heap_diagnostics.c'), str(harness),
                            '-o', str(binary)], check=True, capture_output=True, text=True)
            for failure in range(5):
                subprocess.run([str(binary), str(failure)], check=True,
                               capture_output=True, text=True)
            # Production build has no trace/API dependencies or allocation.
            (root / 'sdkconfig.h').write_text('#define CONFIG_HEAP_TRACING_STANDALONE 0\n')
            subprocess.run(['cc', '-std=c11', '-Werror', '-I', str(root), '-I', str(NATIVE),
                            '-c', str(NATIVE / 'iotmd_heap_diagnostics.c'),
                            '-o', str(root / 'disabled.o')], check=True, capture_output=True)

    def test_tracing_is_explicit_opt_in_and_not_a_security_override(self):
        cmake = (ROOT / 'firmware/boards/IOTMD_ESP32_S3/mpconfigboard.cmake').read_text()
        self.assertIn('if(IOTMD_HEAP_TRACE)', cmake)
        normal = (ROOT / 'firmware/boards/IOTMD_ESP32_S3/sdkconfig.board').read_text()
        self.assertNotIn('CONFIG_HEAP_TRACING_STANDALONE=y', normal)
        fragment = (ROOT / 'firmware/boards/IOTMD_ESP32_S3/sdkconfig.heap-trace').read_text()
        self.assertIn('CONFIG_HEAP_TRACING_STACK_DEPTH=6', fragment)
        self.assertIn('CONFIG_HEAP_TRACE_HASH_MAP_IN_EXT_RAM=y', fragment)
        self.assertNotIn('CONFIG_SECURE_', fragment)
