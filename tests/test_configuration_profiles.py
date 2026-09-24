import unittest

import configuration_profiles
from services.configuration_profile_service import ConfigurationProfileService


class Credentials:
    def __init__(self):
        self.previewed = None
        self.updated = None

    def preview_operational_settings(self, values):
        self.previewed = dict(values)

    def update_operational_settings(self, values):
        self.updated = dict(values)


class Timezone:
    @staticmethod
    def offset_minutes(name):
        return 60 if name == 'Europe/London' else 0


class Health:
    def __init__(self):
        self.events = []

    def record_event(self, *args, **kwargs):
        self.events.append((args, kwargs))


class ConfigurationProfileTests(unittest.TestCase):
    def test_service_validates_applies_and_audits_profile(self):
        credentials = Credentials()
        health = Health()
        restart_reasons = []
        service = ConfigurationProfileService(
            credentials, Timezone(), health, restart_reasons.append
        )
        result = service.apply({
            'format_version': 1,
            'name': 'Production',
            'settings': {
                'timezone_name': 'Europe/London',
                'ntp_servers': ['pool.ntp.org'],
                'ha_discovery': True,
            },
        }, 'Home Assistant')
        self.assertEqual(credentials.previewed, credentials.updated)
        self.assertEqual(credentials.updated['timezone_offset_minutes'], 60)
        self.assertEqual(result['name'], 'Production')
        self.assertTrue(result['restart_required'])
        self.assertEqual(restart_reasons, ['Configuration profile applied'])
        self.assertEqual(health.events[0][0][0], 'configuration_profile_applied')

    def test_profile_format_excludes_secrets_and_network_identity(self):
        for field in ('wifi_password', 'mqtt_password', 'api_clients', 'device_name'):
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, 'unsupported configuration profile setting'
            ):
                configuration_profiles.normalize_profile({
                    'name': 'Unsafe', 'settings': {field: 'secret'},
                })


if __name__ == '__main__':
    unittest.main()
