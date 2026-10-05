"""Core-owned listener supervision and secret-free transport diagnostics."""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import gc


def resource_snapshot():
    result = {}
    try:
        import _iotmd_platform
        result.update(_iotmd_platform.transport_resources())
    except (ImportError, AttributeError):
        pass
    if hasattr(gc, 'mem_free'):
        result['python_free'] = gc.mem_free()
    return result


def report_failure(log_output, service, stage, exc, peer='unknown'):
    """Never include request bodies, URLs, credentials or certificate data."""
    if not log_output:
        return
    try:
        error_number = getattr(exc, 'errno', None)
        if error_number is None and getattr(exc, 'args', ()):
            value = exc.args[0]
            if isinstance(value, int):
                error_number = value
        detail = ('stage=' + str(stage) + '; peer=' + str(peer) +
                  '; error=' + exc.__class__.__name__)
        if error_number is not None:
            detail += '; errno=' + str(error_number)
        for name, value in resource_snapshot().items():
            detail += '; ' + name + '=' + str(value)
        log_output(service, 'Transport', {'log': detail, 'force': True}, 'ERROR')
    except Exception:
        # A diagnostic allocation failure must not prevent socket cleanup.
        pass


def is_serving(server):
    if server is None:
        return False
    probe = getattr(server, 'is_serving', None)
    if probe:
        return bool(probe())
    task = getattr(server, 'task', None)
    return task is not None and not task.done()


class SupervisedServer:
    def __init__(self, factory, log_output, service, check_seconds=5):
        self.factory = factory
        self.log_output = log_output
        self.service = service
        self.check_seconds = check_seconds
        self.server = None
        self.monitor = None
        self.closed = False

    async def _open(self):
        self.server = await self.factory()
        # The pinned core forwards TLS-wrap failures here, rather than only
        # printing them on UART. CPython's Server has no such hook.
        if hasattr(self.server, 'transport_error_handler'):
            self.server.transport_error_handler = self._transport_error

    def _transport_error(self, stage, address, exc):
        peer = address[0] if isinstance(address, tuple) else address
        report_failure(self.log_output, self.service, stage, exc, peer)

    async def start(self):
        await self._open()
        self.monitor = asyncio.create_task(self._supervise())
        return self

    def is_serving(self):
        return not self.closed and is_serving(self.server)

    def close(self):
        self.closed = True
        if self.monitor:
            self.monitor.cancel()
        if self.server:
            self.server.close()

    async def wait_closed(self):
        if self.monitor:
            try:
                await self.monitor
            except asyncio.CancelledError:
                pass
        if self.server:
            try:
                await self.server.wait_closed()
            except asyncio.CancelledError:
                pass
            except Exception:
                # A failed accept task is already reported by supervision.
                pass

    async def _supervise(self):
        retry_seconds = self.check_seconds
        while not self.closed:
            await asyncio.sleep(retry_seconds)
            if self.closed or self.is_serving():
                retry_seconds = self.check_seconds
                continue
            # Retrieve the failed task's exception before replacing it. The
            # patched native accept loop has already closed its listening fd.
            if self.server is not None:
                try:
                    await self.server.wait_closed()
                except asyncio.CancelledError as exc:
                    if self.closed:
                        raise
                    report_failure(self.log_output, self.service, 'accept-loop', exc)
                except Exception as exc:
                    report_failure(self.log_output, self.service, 'accept-loop', exc)
                else:
                    report_failure(self.log_output, self.service, 'accept-loop',
                                   RuntimeError())
                self.server = None
            try:
                await self._open()
            except Exception as exc:
                report_failure(self.log_output, self.service, 'listener-restart', exc)
                retry_seconds = min(60, retry_seconds * 2)
            else:
                retry_seconds = self.check_seconds
                if self.log_output:
                    try:
                        self.log_output(self.service, 'Transport',
                                        {'log': 'Listener restarted without reboot',
                                         'force': True}, 'INFO')
                    except Exception:
                        pass


async def start_server(handler, host, port, backlog=4, ssl=None,
                       log_output=None, service='TLS'):
    async def factory():
        return await asyncio.start_server(handler, host, port, backlog=backlog, ssl=ssl)
    return await SupervisedServer(factory, log_output, service).start()
