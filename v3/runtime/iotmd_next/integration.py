"""Production composition root for compatibility, shadow and active v3 modes."""

from .cutover import CutoverCoordinator
from .kernel import ApplicationKernel
from .product_transports import build_service_factories
from .shadow import ShadowRuntime


class ProductionComposition:
    """Wire concrete adapters once, keeping policy out of transport code."""

    def __init__(self, platform, namespace, adapters, connectivity,
                 driver_factories, identity, fleet, migration, qualification,
                 compatibility, recovery):
        self._platform = platform
        self._adapters = dict(adapters)
        self._connectivity = connectivity
        self._drivers = dict(driver_factories)
        self._identity = identity
        self._fleet = fleet
        self._migration = migration
        self._qualification = qualification
        self._compatibility = compatibility
        self._recovery = recovery
        self._holder = {'kernel': None}

        def snapshot():
            kernel = self._holder['kernel']
            return {'kernel_state': 'starting', 'health': {'state': 'starting'}} \
                if kernel is None else kernel.snapshot()

        self._service_factories = build_service_factories(
            self._adapters, snapshot, self._connectivity,
            identity, fleet, migration, qualification
        )
        self.coordinator = CutoverCoordinator(
            namespace, platform, self._active_kernel,
            compatibility, recovery, qualification,
            shadow_factory=lambda: ShadowRuntime(compatibility.snapshot)
        )

    def _active_kernel(self):
        kernel = ApplicationKernel(
            self._platform, self._drivers, self._service_factories,
            {'identity': lambda unused: self._identity,
             'fleet': lambda unused: self._fleet},
        )
        self._holder['kernel'] = kernel
        return kernel

    def boot(self, configuration):
        return self.coordinator.boot(configuration)

    def poll(self):
        return self.coordinator.poll()

    def request_mode(self, mode):
        return self.coordinator.request_mode(mode)

    def snapshot(self):
        value = self.coordinator.snapshot()
        value['implementation'] = {
            'paired_update': bool(
                self._platform.capabilities()['updates']['native_pair_journal']
            ),
            'recovery': bool(
                self._platform.capabilities()['recovery']['product_independent']
            ),
            'native_jobs': bool(
                self._platform.capabilities()['jobs']['async_worker']
            ),
            'physical_resources': bool(
                self._platform.capabilities()['resources']['physical']
            ),
            'transports': len(self._adapters),
            'identity': self._identity is not None,
            'fleet': self._fleet is not None,
            'migration': self._migration is not None,
            'drivers': len(self._drivers),
            'cutover': True,
        }
        return value
