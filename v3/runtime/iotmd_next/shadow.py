"""Side-effect-free v3 shadow validation beside the compatibility runtime."""

from .configuration import migrate_configuration


class ShadowRuntime:
    """Validate and compare v3 projections without opening transports/hardware."""

    def __init__(self, compatibility_snapshot, maximum_differences=16):
        if not callable(compatibility_snapshot):
            raise ValueError('compatibility snapshot is unavailable')
        self._compatibility_snapshot = compatibility_snapshot
        self._maximum = max(1, min(32, int(maximum_differences)))
        self._configuration = None
        self._polls = 0
        self._differences = []
        self._state = 'idle'

    def boot(self, configuration):
        self._configuration = migrate_configuration(configuration)['configuration']
        self._state = 'running'
        self._compare()

    def _compare(self):
        live = self._compatibility_snapshot() or {}
        expected_name = self._configuration['device']['name']
        actual_name = str(
            live.get('device_name', live.get('device', expected_name))
        )
        differences = []
        if actual_name != expected_name:
            differences.append('device-name')
        live_modules = live.get('modules', ())
        if isinstance(live_modules, dict):
            live_modules = live_modules.get('items', ())
        expected_modules = len([
            item for item in self._configuration['modules'] if item['enabled']
        ])
        if isinstance(live_modules, (list, tuple)) and len(live_modules) != expected_modules:
            differences.append('module-count')
        self._differences = differences[:self._maximum]

    def poll(self):
        if self._state != 'running':
            raise RuntimeError('shadow runtime is not running')
        self._polls += 1
        self._compare()

    def shutdown(self):
        self._state = 'stopped'

    def snapshot(self):
        return {
            'contract_version': 1, 'kernel_state': self._state,
            'health': {
                'state': 'degraded' if self._differences else
                    ('healthy' if self._state == 'running' else 'inactive'),
                'services_total': 0,
                'services_degraded': len(self._differences),
                'services_failed': 0,
            },
            'services': (), 'resources': (), 'events': (),
            'shadow': {
                'polls': self._polls,
                'differences': list(self._differences),
                'side_effects': False,
            },
        }
