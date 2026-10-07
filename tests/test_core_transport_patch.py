"""Exercise the actual versioned patch, not a reimplementation of its logic."""
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.micropython_patches import apply_core_patches, restore_core_patches


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'firmware/patches/tls-listener-cleanup.patch'


def before_patch(patch=PATCH):
    """Reconstruct just the original context needed by git apply from hunks."""
    files, current, active = {}, None, False
    for line in patch.read_text().splitlines():
        if line.startswith('diff --git '):
            current = line.split(' b/', 1)[1]
            files[current] = []
            active = False
        elif line.startswith('@@ '):
            active = True
        elif active and line[:1] in (' ', '-'):
            files[current].append(line[1:] + '\n')
    return {path: ''.join(lines) for path, lines in files.items()}


class CoreTransportPatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.original = before_patch()
        for relative, source in self.original.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)
        self.applied = apply_core_patches(self.root, [PATCH])

    def tearDown(self):
        restore_core_patches(self.root, self.applied)
        for relative, original in self.original.items():
            self.assertEqual((self.root / relative).read_text(), original)
        self.temporary.cleanup()

    def server(self, create_task=lambda value: None):
        source = (self.root / 'extmod/asyncio/stream.py').read_text()
        # MicroPython permits generator-style async def, CPython does not.
        # This accept loop has no await; drive exactly its yielded IO waits.
        source = source.split('# Helper function', 1)[0]
        source = source.replace('async def _serve(', 'def _serve(')
        errors = []
        core = SimpleNamespace(
            _io_queue=SimpleNamespace(queue_read=lambda sock: 'io-wait'),
            CancelledError=type('CancelledError', (BaseException,), {}),
            sys=SimpleNamespace(print_exception=lambda exc: errors.append(exc)),
            create_task=create_task,
        )
        namespace = {'core': core, 'Stream': lambda sock, extra: sock}
        exec('class Server:\n' + source, namespace)
        return namespace['Server'](), errors

    def test_tls_wrap_memory_failure_closes_peer_and_keeps_accepting(self):
        server, errors = self.server()
        peer = SimpleNamespace(close_count=0)
        def close():
            peer.close_count += 1
        peer.close = close
        listener = SimpleNamespace(accept=lambda: (peer, ('192.0.2.1', 5)), close=lambda: None)
        def fail_wrap(*args, **kwargs):
            raise MemoryError()
        loop = server._serve(listener, lambda *args: None,
                             SimpleNamespace(wrap_socket=fail_wrap))
        self.assertEqual(next(loop), 'io-wait')
        diagnostics = []
        server.transport_error_handler = lambda *args: diagnostics.append(args)
        self.assertEqual(next(loop), 'io-wait')
        self.assertEqual(peer.close_count, 1)
        self.assertEqual(diagnostics[0][0], 'tls-wrap')
        self.assertEqual(errors, [])
        loop.close()

    def test_failed_task_creation_closes_both_peer_and_listener(self):
        def fail_task(value):
            raise MemoryError()
        server, unused = self.server(fail_task)
        closed = []
        peer = SimpleNamespace(setblocking=lambda value: None,
                               close=lambda: closed.append('peer'))
        listener = SimpleNamespace(accept=lambda: (peer, ('192.0.2.1', 5)),
                                   close=lambda: closed.append('listener'))
        loop = server._serve(listener, lambda *args: None, None)
        next(loop)
        with self.assertRaises(MemoryError):
            next(loop)
        self.assertEqual(closed, ['peer', 'listener'])

    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_native_fatal_handshake_closes_tcp_once_and_preserves_errno(self):
        source = (self.root / 'extmod/modtls_mbedtls.c').read_text()
        helper = re.search(r'static void ssl_close_failed_handshake.*?\n}', source, re.S).group()
        harness = textwrap.dedent('''
            #include <assert.h>
            #include <stdint.h>
            typedef void *mp_obj_t;
            #define MP_OBJ_NULL ((void *)0)
            #define MP_STREAM_CLOSE 7
            typedef struct { mp_obj_t sock; int ssl; } mp_obj_ssl_socket_t;
            static int closes, frees;
            static uintptr_t close_socket(mp_obj_t sock, int request, uintptr_t arg, int *err) {
                assert(request == MP_STREAM_CLOSE);
                assert(sock != MP_OBJ_NULL);
                ++closes;
                *err = 99; // Must not overwrite the original TLS error.
                return 0;
            }
            struct stream { uintptr_t (*ioctl)(mp_obj_t, int, uintptr_t, int *); };
            static struct stream stream = { close_socket };
            static struct stream *mp_get_stream(mp_obj_t sock) { return &stream; }
            static void mbedtls_ssl_free(int *ssl) { ++frees; }
        ''') + helper + textwrap.dedent('''
            int main(void) {
                int tls_error = -1;
                mp_obj_ssl_socket_t socket = { (void *)1, 0 };
                ssl_close_failed_handshake(&socket);
                assert(socket.sock == MP_OBJ_NULL);
                assert(closes == 1 && frees == 1 && tls_error == -1);
                ssl_close_failed_handshake(&socket);
                assert(closes == 1);
                return 0;
            }
        ''')
        binary = self.root / 'native-test'
        subprocess.run(['cc', '-x', 'c', '-', '-o', str(binary)], input=harness,
                       text=True, check=True, capture_output=True)
        subprocess.run([str(binary)], check=True)
        self.assertEqual(source.count('ssl_close_failed_handshake(sslsock);'), 2)

    def test_mismatched_source_is_rejected_without_modifying_another_file(self):
        restore_core_patches(self.root, self.applied)
        self.applied = []
        native = self.root / 'extmod/modtls_mbedtls.c'
        native.write_text('unrelated developer change\n')
        with self.assertRaises(subprocess.CalledProcessError):
            apply_core_patches(self.root, [PATCH])
        self.assertEqual((self.root / 'extmod/asyncio/stream.py').read_text(),
                         self.original['extmod/asyncio/stream.py'])
        self.assertEqual(native.read_text(), 'unrelated developer change\n')
        self.original['extmod/modtls_mbedtls.c'] = native.read_text()
