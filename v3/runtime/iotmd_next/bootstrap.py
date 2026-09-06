"""Executable product bootstrap around the v3 production composition root."""


class BootstrapError(RuntimeError):
    pass


class ProductBootstrap:
    """Own configuration load, one composition, polling and clean shutdown."""

    def __init__(self, composition, configuration_loader, idle,
                 health_marker=None):
        for operation in ('boot', 'poll', 'snapshot'):
            if not callable(getattr(composition, operation, None)):
                raise BootstrapError('production composition is incomplete')
        if not callable(configuration_loader) or not callable(idle):
            raise BootstrapError('product bootstrap dependency is unavailable')
        if health_marker is not None and not callable(health_marker):
            raise BootstrapError('product health marker is invalid')
        self._composition = composition
        self._configuration_loader = configuration_loader
        self._idle = idle
        self._health_marker = health_marker
        self._state = 'idle'
        self._polls = 0
        self._failure = ''

    def start(self):
        if self._state not in ('idle', 'stopped'):
            raise BootstrapError('product bootstrap is already started')
        self._state = 'starting'
        try:
            configuration = self._configuration_loader()
            if not isinstance(configuration, dict):
                raise BootstrapError('product configuration is invalid')
            result = self._composition.boot(configuration)
            self._state = 'running'
            self._failure = ''
            if self._health_marker is not None:
                self._health_marker()
            return result
        except Exception as exc:
            self._state = 'failed'
            self._failure = str(exc)[:160]
            raise

    def poll(self):
        if self._state != 'running':
            raise BootstrapError('product bootstrap is not running')
        self._composition.poll()
        self._polls += 1
        return self.snapshot()

    def run(self, maximum_cycles=None):
        self.start()
        cycles = None if maximum_cycles is None else max(0, int(maximum_cycles))
        while self._state == 'running' and (cycles is None or self._polls < cycles):
            self.poll()
            self._idle()
        return self.snapshot()

    def stop(self):
        stopper = getattr(self._composition, 'stop', None)
        if callable(stopper):
            stopper()
        self._state = 'stopped'
        return self.snapshot()

    def snapshot(self):
        return {
            'state': self._state, 'polls': self._polls,
            'failure': self._failure,
            'composition': self._composition.snapshot(),
        }
