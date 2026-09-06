import unittest
from types import SimpleNamespace

from services.startup_service import StartupService
from v3.runtime.iotmd_next.native_pair import (
    NativePairCoordinator, NativePairError,
)
from v3.runtime.iotmd_next.production_drivers import (
    validate_complete_driver_catalog,
)
from v3.runtime.iotmd_next.production_migration import (
    ProductionMigrationStaging,
)
from v3.runtime.iotmd_next.shadow import ShadowRuntime


class PairPlatform:
    def __init__(self):
        self.state = {
            'phase': 'idle', 'sequence': 0, 'pair_id': '',
            'platform_label': '', 'runtime_slot': '',
            'previous_runtime_slot': '', 'runtime_healthy': False,
            'failure': '',
        }

    def capabilities(self):
        return {'updates': {'native_pair_journal': True}}

    def pair_snapshot(self): return dict(self.state)

    def prepare_pair(self, pair_id, sequence, platform, runtime, previous):
        self.state.update(
            phase='prepared', pair_id=pair_id, sequence=sequence,
            platform_label=platform, runtime_slot=runtime,
            previous_runtime_slot=previous, runtime_healthy=False,
        )
        return self.pair_snapshot()

    def begin_pair_trial(self, pair_id, runtime):
        self.state['phase'] = 'trial'
        return self.pair_snapshot()

    def mark_pair_runtime_healthy(self, pair_id, runtime):
        self.state['runtime_healthy'] = True
        return True

    def confirm_pair(self, pair_id):
        self.state['phase'] = 'confirmed'
        return True

    def request_pair_rollback(self, pair_id, reason):
        self.state['phase'] = 'rollback'
        self.state['failure'] = reason
        return self.pair_snapshot()

    def complete_pair_rollback(self, pair_id, restored):
        self.state['phase'] = 'rolled-back'
        return True


class RuntimeSlots:
    def __init__(self): self.slot = 'a'
    def current_slot(self): return self.slot
    def activate(self, slot): self.slot = slot
    def restore(self):
        self.slot = 'a'
        return self.slot


class RemainingGateTests(unittest.TestCase):
    @staticmethod
    def _startup():
        return StartupService(None, None, None, None, lambda *unused: None)

    def test_native_pair_requires_runtime_health_before_confirmation(self):
        platform = PairPlatform()
        slots = RuntimeSlots()
        pair = NativePairCoordinator(platform, slots)
        pair.prepare('pair-10', 10, 'ota_1', 'b')
        pair.begin_trial('pair-10', 'b')
        self.assertTrue(pair.confirm('pair-10'))
        self.assertEqual(pair.snapshot()['phase'], 'confirmed')
        self.assertTrue(pair.snapshot()['runtime_healthy'])

    def test_native_pair_fails_closed_on_running_runtime_mismatch(self):
        platform = PairPlatform()
        slots = RuntimeSlots()
        pair = NativePairCoordinator(platform, slots)
        pair.prepare('pair-10', 10, 'ota_1', 'b')
        platform.state['phase'] = 'trial'
        with self.assertRaisesRegex(NativePairError, 'does not match'):
            pair.confirm('pair-10')

    def test_migration_staging_activates_only_known_complete_handles(self):
        activated = []
        discarded = []
        next_handle = [0]

        def stage(section, payload):
            next_handle[0] += 1
            return next_handle[0]

        adapter = ProductionMigrationStaging(
            stage, lambda handles: activated.extend(handles),
            lambda handles: discarded.extend(handles)
        )
        handles = [adapter.stage('credentials', {}),
                   adapter.stage('module_settings', {})]
        adapter.activate(handles)
        self.assertEqual(activated, handles)
        self.assertEqual(adapter.snapshot()['staged'], 0)
        with self.assertRaisesRegex(ValueError, 'handle'):
            adapter.discard(handles)

    def test_all_declared_driver_variants_have_v3_catalog_entries(self):
        self.assertEqual(validate_complete_driver_catalog(), {
            'variants': 13, 'drivers': 11,
        })

    def test_shadow_runtime_has_no_transport_or_hardware_side_effects(self):
        runtime = ShadowRuntime(lambda: {
            'device_name': 'iot-md-001', 'modules': [],
        })
        runtime.boot({
            'version': 0, 'device_name': 'iot-md-001', 'modules': [],
        })
        snapshot = runtime.snapshot()
        self.assertTrue(snapshot['shadow']['side_effects'] is False)
        self.assertEqual(snapshot['health']['state'], 'healthy')

    def test_paired_confirmation_commits_native_before_component_metadata(self):
        calls = []
        app = SimpleNamespace(
            update_status=lambda: {'status': 'trial'},
            running_release_sequence=lambda: 0,
            confirm_update=lambda prepare=False:
                calls.append('prepare-runtime' if prepare else 'commit-runtime')
                or True,
        )
        firmware = SimpleNamespace(
            confirm_after_native_pair=lambda:
                calls.append('commit-platform') or True,
            running_release_sequence=lambda: 0,
        )
        universal = SimpleNamespace(
            update_status=lambda: {
                'status': 'activating', 'application_required': True,
                'firmware_required': True, 'application_sequence': 10,
                'firmware_sequence': 10,
            },
            confirm_native_pair=lambda: calls.append('confirm-native') or True,
            confirm_update=lambda: calls.append('confirm-universal') or True,
            rollback_native_pair=lambda reason: calls.append('rollback'),
        )
        recovery = SimpleNamespace(
            mark_application_healthy=lambda: calls.append('healthy')
        )
        self.assertEqual(
            self._startup().confirm_updates(
                firmware, app, universal, recovery
            ),
            (True, True),
        )
        self.assertEqual(calls, [
            'prepare-runtime', 'confirm-native', 'commit-platform',
            'commit-runtime', 'confirm-universal', 'healthy',
        ])

    def test_paired_confirmation_failure_rolls_back_without_health_marker(self):
        calls = []
        app = SimpleNamespace(
            update_status=lambda: {'status': 'trial'},
            running_release_sequence=lambda: 0,
            confirm_update=lambda prepare=False:
                calls.append('prepare-runtime') or True,
        )
        firmware = SimpleNamespace(running_release_sequence=lambda: 0)
        universal = SimpleNamespace(
            update_status=lambda: {
                'status': 'activating', 'application_required': True,
                'firmware_required': True, 'application_sequence': 10,
                'firmware_sequence': 10,
            },
            confirm_native_pair=lambda: False,
            rollback_native_pair=lambda reason: calls.append('rollback'),
        )
        recovery = SimpleNamespace(
            mark_application_healthy=lambda: calls.append('healthy')
        )
        self.assertEqual(
            self._startup().confirm_updates(
                firmware, app, universal, recovery
            ),
            (False, False),
        )
        self.assertEqual(calls, ['prepare-runtime', 'rollback'])


if __name__ == '__main__':
    unittest.main()
