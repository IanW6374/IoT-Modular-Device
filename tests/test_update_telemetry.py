import unittest
from types import SimpleNamespace

from device_api_inventory import DeviceInventory
from update_telemetry import UpdateTelemetry
from release_selection import for_target


class UpdateTelemetryTests(unittest.TestCase):
    def test_exact_release_target_does_not_choose_a_different_type_or_version(self):
        releases = [
            {'release_sequence': 2804, 'type': 'application'},
            {'release_sequence': 2804, 'type': 'universal'},
            {'release_sequence': 2805, 'type': 'universal'},
        ]
        self.assertEqual(for_target(releases, 2804, 'universal'), [releases[1]])
        self.assertEqual(for_target(releases, 2806, 'universal'), [])

    def test_byte_completion_does_not_confirm_verification(self):
        telemetry = UpdateTelemetry()
        telemetry.begin({'type': 'universal', 'release_sequence': 2804})
        telemetry.record('firmware_writing', 100, 100)
        self.assertNotIn('core_write', telemetry.progress['completed'])
        telemetry.record('firmware_verification', 100, 100)
        self.assertIn('core_write', telemetry.progress['completed'])
        self.assertNotIn('core_verify', telemetry.progress['completed'])
        telemetry.record('application_receiving', 10, 100)
        self.assertIn('core_verify', telemetry.progress['completed'])
        telemetry.failed()
        self.assertTrue(telemetry.progress['failed'])
        self.assertNotIn('pair', telemetry.progress['completed'])

    def test_rebooted_trial_preserves_pair_boundary_not_activation_success(self):
        telemetry = UpdateTelemetry()
        app = SimpleNamespace(update_status=lambda: {'status': 'trial'})
        core = SimpleNamespace(update_status=lambda: {'status': 'trial'})
        pair = SimpleNamespace(update_status=lambda: {
            'status': 'activating', 'release_sequence': 2804,
            'confirmation_phase': 'application-loaded',
        })
        result = telemetry.snapshot(app, core, pair)
        self.assertIn('pair', result['completed'])
        self.assertNotIn('install', result['completed'])
        self.assertEqual(result['application_status'], 'trial')
        self.assertEqual(result['phase'], 'install')
        result['completed'].clear()
        self.assertIn('pair', telemetry.snapshot(app, core, pair)['completed'])

    def test_inventory_exports_description_and_progress(self):
        value = DeviceInventory({'device_description': 'Heating controller',
                                 'update_progress': {'phase': 'core_verify'}})
        self.assertEqual(value.info()['device_description'], 'Heating controller')
        self.assertEqual(value.configuration()['device_description'], 'Heating controller')
        self.assertEqual(value.info()['update_progress']['phase'], 'core_verify')
