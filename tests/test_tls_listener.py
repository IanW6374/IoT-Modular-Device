import asyncio
import unittest
from unittest import mock

import tls_listener


class FakeServer:
    def __init__(self):
        self.serving = True
        self.closed = False
        self.failure = None
        self.transport_error_handler = None

    def is_serving(self):
        return self.serving and not self.closed

    def close(self):
        self.closed = True

    async def wait_closed(self):
        if self.failure:
            raise self.failure


class TLSListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_dead_accept_loop_restarts_and_reports_real_status(self):
        first, second = FakeServer(), FakeServer()
        calls, logs = [], []

        async def factory():
            calls.append(True)
            return first if len(calls) == 1 else second

        listener = await tls_listener.SupervisedServer(
            factory, lambda *args: logs.append(args), 'API', .001
        ).start()
        self.assertTrue(listener.is_serving())
        first.failure = MemoryError('secret-not-for-logs')
        first.serving = False
        self.assertFalse(listener.is_serving())
        for unused in range(50):
            if len(calls) == 2:
                break
            await asyncio.sleep(.001)
        self.assertEqual(len(calls), 2)
        self.assertTrue(listener.is_serving())
        self.assertIn('stage=accept-loop', logs[0][2]['log'])
        self.assertNotIn('secret-not-for-logs', str(logs))
        listener.close()
        await listener.wait_closed()
        self.assertTrue(second.closed)

    async def test_rebind_failure_is_retried_without_duplicate_accept_failures(self):
        first, second = FakeServer(), FakeServer()
        calls, logs = [], []

        async def factory():
            calls.append(True)
            if len(calls) == 2:
                raise OSError(98)
            return first if len(calls) == 1 else second

        listener = await tls_listener.SupervisedServer(
            factory, lambda *args: logs.append(args), 'Portal', .001
        ).start()
        first.serving = False
        for unused in range(50):
            if len(calls) == 3:
                break
            await asyncio.sleep(.001)
        self.assertTrue(listener.is_serving())
        self.assertEqual(sum('stage=accept-loop' in args[2]['log'] for args in logs), 1)
        self.assertIn('stage=listener-restart', logs[1][2]['log'])
        listener.close()
        await listener.wait_closed()

    async def test_healthy_or_intentionally_closed_listener_is_not_restarted(self):
        server = FakeServer()
        factory = mock.AsyncMock(return_value=server)
        listener = await tls_listener.SupervisedServer(factory, None, 'API', .001).start()
        await asyncio.sleep(.005)
        listener.close()
        await listener.wait_closed()
        await asyncio.sleep(.003)
        self.assertEqual(factory.await_count, 1)
        self.assertFalse(listener.is_serving())

    async def test_unexpected_accept_task_cancellation_is_supervised(self):
        first, second = FakeServer(), FakeServer()
        factory = mock.AsyncMock(side_effect=[first, second])
        listener = await tls_listener.SupervisedServer(factory, None, 'API', .001).start()
        first.failure = asyncio.CancelledError()
        first.serving = False
        for unused in range(50):
            if factory.await_count == 2:
                break
            await asyncio.sleep(.001)
        self.assertTrue(listener.is_serving())
        listener.close()
        await listener.wait_closed()

    async def test_native_wrap_diagnostics_include_errno_peer_and_internal_memory(self):
        logs = []
        listener = tls_listener.SupervisedServer(None, lambda *args: logs.append(args), 'API')
        with mock.patch.object(tls_listener, 'resource_snapshot', return_value={
            'internal_free': 3000, 'dma_largest': 1000
        }):
            listener._transport_error('tls-wrap', ('192.0.2.1', 1234), OSError(1))
        detail = logs[0][2]['log']
        self.assertIn('stage=tls-wrap', detail)
        self.assertIn('peer=192.0.2.1', detail)
        self.assertIn('errno=1', detail)
        self.assertIn('dma_largest=1000', detail)

    async def test_logging_failure_cannot_break_listener_or_cleanup(self):
        def broken_logger(*args):
            raise MemoryError()
        tls_listener.report_failure(broken_logger, 'API', 'tls-wrap', OSError(1))

    async def test_health_uses_accept_task_on_micropython(self):
        server = type('Server', (), {'task': mock.Mock()})()
        server.task.done.return_value = False
        self.assertTrue(tls_listener.is_serving(server))
        server.task.done.return_value = True
        self.assertFalse(tls_listener.is_serving(server))
        self.assertFalse(tls_listener.is_serving(None))
