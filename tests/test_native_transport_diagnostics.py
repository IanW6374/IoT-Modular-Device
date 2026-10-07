"""Compile and execute the real fixed-size native diagnostic implementation."""
import shutil
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_core_transport_patch import before_patch
from tools.micropython_patches import apply_core_patches, restore_core_patches


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'firmware/native'


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class NativeTransportDiagnosticsTests(unittest.TestCase):
    def test_actual_patch_excludes_normal_tls_wait_and_close_results(self):
        patch = ROOT / 'firmware/patches/transport-diagnostics.patch'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            originals = before_patch(patch)
            for relative, source in originals.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            applied = apply_core_patches(root, [patch])
            try:
                source = (root / 'extmod/modtls_mbedtls.c').read_text()
                helper = re.search(r'static void tls_diagnostic_result.*?\n}', source, re.S).group()
                harness = root / 'tls-results.c'
                harness.write_text('''
                    #include <assert.h>
                    #include <stdbool.h>
                    #define MBEDTLS_SSL_PROTO_TLS1_3 1
                    #define MBEDTLS_ERR_SSL_WANT_READ -1
                    #define MBEDTLS_ERR_SSL_WANT_WRITE -2
                    #define MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY -3
                    #define MBEDTLS_ERR_SSL_CONN_EOF -4
                    #define MBEDTLS_ERR_SSL_RECEIVED_NEW_SESSION_TICKET -5
                    typedef struct { int ssl; } mp_obj_ssl_socket_t;
                    static bool failed, established;
                    static int recorded;
                    static int mbedtls_ssl_is_handshake_over(int *ssl) { return *ssl; }
                    static void iotmd_transport_tls_leave(void *socket, int result, bool ready, bool error) {
                        failed = error;
                        established = ready;
                        recorded = result;
                    }
                ''' + helper + '''
                    int main(void) {
                        mp_obj_ssl_socket_t socket = {0};
                        for (int ret = -1; ret >= -5; --ret) {
                            tls_diagnostic_result(&socket, ret);
                            assert(recorded == ret && !failed && !established);
                        }
                        tls_diagnostic_result(&socket, -100);
                        assert(failed && recorded == -100);
                        socket.ssl = 1;
                        tls_diagnostic_result(&socket, 123);
                        assert(!failed && established && recorded == 123);
                        return 0;
                    }
                ''')
                binary = root / 'tls-results'
                subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                                '-Wno-unused-parameter', str(harness), '-o', str(binary)],
                               check=True, capture_output=True, text=True)
                subprocess.run([str(binary)], check=True)
                self.assertIn('iotmd_transport_tls_close(self);', source)
                self.assertEqual(source.count('iotmd_transport_tls_close(o);'), 2)
                self.assertIn('iotmd_transport_tls_enter(o, IOTMD_TLS_READ);', source)
                self.assertIn('iotmd_transport_tls_enter(o, IOTMD_TLS_WRITE);', source)
            finally:
                restore_core_patches(root, applied)
                for relative, source in originals.items():
                    self.assertEqual((root / relative).read_text(), source)

    def test_counters_timers_closure_overflow_and_clock_wrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'freertos').mkdir()
            stubs = {
                'sdkconfig.h': '#define CONFIG_LWIP_MAX_SOCKETS 10\n',
                'freertos/FreeRTOS.h': '''
                    typedef int portMUX_TYPE;
                    #define portMUX_INITIALIZER_UNLOCKED 0
                    #define portENTER_CRITICAL(lock) ((void)(lock))
                    #define portEXIT_CRITICAL(lock) ((void)(lock))
                ''',
                'esp_timer.h': '''
                    #include <stdbool.h>
                    #include <stdint.h>
                    #define ESP_OK 0
                    typedef void *esp_timer_handle_t;
                    typedef struct {
                        void (*callback)(void *);
                        const char *name;
                        bool skip_unhandled_events;
                    } esp_timer_create_args_t;
                    int64_t esp_timer_get_time(void);
                    int esp_timer_create(const esp_timer_create_args_t *, esp_timer_handle_t *);
                    int esp_timer_start_periodic(esp_timer_handle_t, uint64_t);
                    int esp_timer_delete(esp_timer_handle_t);
                ''',
                'esp_heap_caps.h': '''
                    #include <stdint.h>
                    #define MALLOC_CAP_INTERNAL 1
                    #define MALLOC_CAP_8BIT 2
                    unsigned heap_caps_get_free_size(uint32_t);
                    unsigned heap_caps_get_largest_free_block(uint32_t);
                    unsigned heap_caps_get_minimum_free_size(uint32_t);
                ''',
                'esp_log.h': '''
                    #define ESP_LOG_WARN 2
                    #define ESP_LOG_INFO 3
                    void diagnostic_log(int, const char *, const char *, ...);
                    #define ESP_LOG_LEVEL(level, tag, ...) diagnostic_log(level, tag, __VA_ARGS__)
                ''',
            }
            for name, contents in stubs.items():
                (root / name).write_text(contents)
            harness = root / 'test.c'
            harness.write_text(r'''
                #include <assert.h>
                #include <stdarg.h>
                #include <stdio.h>
                #include <string.h>
                #include "esp_timer.h"
                #include "iotmd_transport_diagnostics.h"
                static uint64_t clock_ms = 1000;
                static void (*timer_callback)(void *);
                static int reports, timer_creates;
                static unsigned largest = 8192;
                static char message[1024];
                int64_t esp_timer_get_time(void) { return clock_ms * 1000; }
                int esp_timer_create(const esp_timer_create_args_t *args, esp_timer_handle_t *out) {
                    assert(args->skip_unhandled_events);
                    timer_callback = args->callback;
                    *out = (void *)1;
                    ++timer_creates;
                    return 0;
                }
                int esp_timer_start_periodic(esp_timer_handle_t h, uint64_t us) {
                    assert(h && us == 10000000);
                    return 0;
                }
                int esp_timer_delete(esp_timer_handle_t h) { return 0; }
                unsigned heap_caps_get_free_size(uint32_t caps) { return 43000; }
                unsigned heap_caps_get_largest_free_block(uint32_t caps) { return largest; }
                unsigned heap_caps_get_minimum_free_size(uint32_t caps) { return 40000; }
                void diagnostic_log(int level, const char *tag, const char *format, ...) {
                    va_list args;
                    va_start(args, format);
                    vsnprintf(message, sizeof(message), format, args);
                    va_end(args);
                    ++reports;
                    assert(strcmp(tag, "IoT-MD-Transport") == 0);
                    assert(strstr(message, "internal_largest="));
                }
                int main(void) {
                    iotmd_transport_snapshot_t s;
                    iotmd_transport_heartbeat();
                    iotmd_transport_heartbeat();
                    assert(timer_creates == 1);
                    clock_ms = 60000;
                    timer_callback(NULL);
                    assert(reports == 0); // Intentionally disabled listeners.
                    iotmd_transport_socket_open(-1);
                    iotmd_transport_socket_open(3);
                    iotmd_transport_socket_open(3);
                    iotmd_transport_socket_listen(3);
                    iotmd_transport_accept(4, 0);
                    iotmd_transport_socket_open(4);
                    iotmd_transport_accept(-1, 0); // EAGAIN is not an error.
                    iotmd_transport_accept(-1, 1);
                    iotmd_transport_tls_open((void *)1);
                    iotmd_transport_tls_open((void *)1);
                    iotmd_transport_heartbeat();
                    iotmd_transport_tls_enter((void *)1, IOTMD_TLS_READ);
                    clock_ms += 20000;
                    iotmd_transport_snapshot(&s);
                    assert(s.sockets == 2 && s.listeners == 1 && s.socket_limit == 10);
                    assert(s.socket_opens == 2 && s.accepts == 1 && s.accept_errors == 1);
                    assert(s.tls_active == 1 && s.tls_pending == 1 && s.tls_opens == 1);
                    assert(s.tls_call_ms == 20000 && s.tls_call_stage == IOTMD_TLS_READ);
                    assert(s.vm_heartbeat_age_ms == 20000 && s.tls_wait_ms == 20000);
                    timer_callback(NULL);
                    assert(reports == 1 && strstr(message, "call_stage=3"));
                    clock_ms += 10000;
                    timer_callback(NULL);
                    assert(reports == 1); // Warning rate limit.
                    clock_ms += 20000;
                    timer_callback(NULL);
                    assert(reports == 2);
                    iotmd_transport_tls_leave((void *)1, -100, false, false);
                    iotmd_transport_snapshot(&s);
                    assert(s.tls_call_stage == 0 && s.tls_errors == 0);
                    iotmd_transport_tls_leave((void *)1, 20, true, false);
                    iotmd_transport_snapshot(&s);
                    assert(s.tls_pending == 0 && s.tls_wait_ms == 0);
                    assert(s.tls_last_progress_age_ms == 0);
                    iotmd_transport_tls_leave((void *)1, -123, false, true);
                    iotmd_transport_tls_close((void *)1);
                    iotmd_transport_tls_close((void *)1);
                    iotmd_transport_socket_close(4);
                    iotmd_transport_socket_close(4);
                    iotmd_transport_snapshot(&s);
                    assert(s.tls_active == 0 && s.tls_closes == 1);
                    assert(s.tls_errors == 1 && s.tls_last_error == -123);
                    assert(s.sockets == 1 && s.socket_closes == 1);
                    // File descriptor reuse must not double-count previous sockets.
                    iotmd_transport_socket_open(4);
                    iotmd_transport_snapshot(&s);
                    assert(s.sockets == 2 && s.socket_opens == 3);
                    clock_ms = UINT32_MAX - 100;
                    iotmd_transport_heartbeat();
                    iotmd_transport_tls_open((void *)2);
                    iotmd_transport_tls_enter((void *)2, IOTMD_TLS_WRITE);
                    clock_ms += 200;
                    iotmd_transport_snapshot(&s);
                    assert(s.vm_heartbeat_age_ms == 200 && s.tls_call_ms == 200);
                    for (int i = 0; i < 20; ++i) {
                        iotmd_transport_socket_open(100 + i);
                    }
                    iotmd_transport_snapshot(&s);
                    assert(s.sockets == 10 && s.tracking_overflows == 12);
                    return 0;
                }
            ''')
            binary = root / 'native-test'
            subprocess.run([
                'cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', '-I', str(root), '-I', str(NATIVE),
                str(NATIVE / 'iotmd_transport_diagnostics.c'), str(harness),
                '-o', str(binary),
            ], check=True, capture_output=True, text=True)
            subprocess.run([str(binary)], check=True, capture_output=True, text=True)
