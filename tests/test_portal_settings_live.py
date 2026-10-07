"""Exercise the actual runtime settings handler without booting hardware."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from services.configuration_profile_service import ConfigurationProfileService


class PortalSettingsLiveTests(unittest.TestCase):
    def setUp(self):
        self.reasons = []
        self.current = {}
        self.trials = []
        self.namespace = {
            'credential_store': SimpleNamespace(
                public_settings=lambda: dict(self.current),
                update_operational_settings=self.save,
            ),
            'timezone_rules': SimpleNamespace(offset_minutes=lambda _: 0),
            'device_settings': SimpleNamespace(device_api_port=8444),
            'mark_restart_required': self.reasons.append,
            'configuration_profile_service': ConfigurationProfileService(None, None, None, self.reasons.append),
            '_configured_portal_login_url': lambda _: '/login',
            'network_trial_timeout_s': 120,
        }
        tree = ast.parse(Path('iotmd_runtime.py').read_text())
        handler = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'update_portal_settings')
        module = ast.Module(body=[handler], type_ignores=[])
        exec(compile(module, 'iotmd_runtime.py', 'exec'), self.namespace)
        self.update = self.namespace['update_portal_settings']
        self.params = {'device_name': 'IoT-MD-001', 'wifi_ssid': 'Test network',
                       'wifi_dhcp': 'on', 'portal_port': '8443'}
        self.update(self.params)
        self.reasons.clear()
        self.trials.clear()

    def save(self, values, network_trial=False):
        updated = dict(values)
        for key in ('mqtt_port', 'portal_port'):
            if updated.get(key):
                updated[key] = int(updated[key])
        for key in ('wifi_password', 'mqtt_password'):
            updated.pop(key, None)  # Public settings never include credentials.
        self.current.update(updated)
        self.trials.append(network_trial)
        return dict(self.current)

    def test_description_changes_and_clearing_are_live(self):
        for description in ('Boiler controller', ''):
            result = self.update({**self.params, 'device_description': description})
            self.assertEqual(self.current['device_description'], description)
            self.assertFalse(result['restart_required'])
            self.assertIn('No restart', result['message'])
        self.assertEqual(self.reasons, [])
        self.assertEqual(self.trials, [False, False])

    def test_unchanged_form_does_not_mark_restart(self):
        self.assertFalse(self.update(self.params)['restart_required'])
        self.assertEqual(self.reasons, [])

    def test_real_configuration_and_secret_changes_still_require_restart(self):
        for changes in ({'mqtt_port': '1883'}, {'wifi_password': 'new-password'},
                        {'mqtt_password': 'new-password'}, {'wifi_ssid': 'New network'}):
            with self.subTest(changes=changes):
                self.assertTrue(self.update({**self.params, **changes})['restart_required'])
        self.assertEqual(len(self.reasons), 4)
        self.assertTrue(self.trials[-1])

    def test_live_save_preserves_preexisting_restart_reasons(self):
        self.reasons.append('Another setting changed')
        self.update({**self.params, 'device_description': 'New label'})
        self.assertEqual(self.reasons, ['Another setting changed'])
