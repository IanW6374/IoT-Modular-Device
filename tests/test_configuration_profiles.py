import unittest

import configuration_profiles
from services.configuration_profile_service import ConfigurationProfileService


class Credentials:
    def __init__(self):
        self.previewed = None
        self.updated = None
        self.network_trial = False

    def preview_operational_settings(self, values):
        self.previewed = dict(values)

    def update_operational_settings(self, values, network_trial=False):
        self.updated = dict(values)
        self.network_trial = network_trial
        return {'network_trial_pending': network_trial}


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
    def test_description_only_profile_does_not_require_restart(self):
        for description in ('Boiler controller', ''):
            with self.subTest(description=description):
                credentials, reasons = Credentials(), []
                service = ConfigurationProfileService(credentials, Timezone(), Health(), reasons.append)
                result = service.apply({'name': 'Description', 'settings': {
                    'device_description': description,
                }}, 'Management')
                self.assertEqual(credentials.updated, {'device_description': description})
                self.assertFalse(result['restart_required'])
                self.assertFalse(credentials.network_trial)
                self.assertEqual(reasons, [])

    def test_mixed_description_profile_still_requires_restart(self):
        reasons = []
        service = ConfigurationProfileService(Credentials(), Timezone(), Health(), reasons.append)
        result = service.apply({'name': 'Mixed', 'settings': {
            'device_description': 'Boiler', 'loglevel': 'INFO',
        }}, 'Management')
        self.assertTrue(result['restart_required'])
        self.assertEqual(reasons, ['Configuration profile applied'])

    def test_portal_control_alignment_preserves_multi_selects(self):
        from web_portal_ui import PORTAL_CSS
        self.assertIn('align-content:start;grid-auto-rows:max-content', PORTAL_CSS)
        self.assertIn('height:42px;min-height:42px', PORTAL_CSS)
        self.assertIn('select:not([multiple]):not([size])', PORTAL_CSS)
        self.assertIn('textarea,select[multiple],select[size]{height:auto}', PORTAL_CSS)

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
                'release_channel': 'alpha',
                'release_check_schedule': 'weekly',
                'release_check_time': '03:30',
                'release_check_weekday': 6,
                'release_auto_download': True,
                'release_auto_activate': False,
            },
            'secrets': {'mqtt_password': 'broker-secret'},
        }, 'Home Assistant')
        self.assertEqual(credentials.previewed, credentials.updated)
        self.assertEqual(credentials.updated['timezone_offset_minutes'], 60)
        self.assertEqual(credentials.updated['release_channel'], 'alpha')
        self.assertEqual(credentials.updated['release_check_time'], '03:30')
        self.assertEqual(credentials.updated['mqtt_password'], 'broker-secret')
        self.assertEqual(result['name'], 'Production')
        self.assertTrue(result['restart_required'])
        self.assertEqual(restart_reasons, ['Configuration profile applied'])
        self.assertEqual(health.events[0][0][0], 'configuration_profile_applied')

    def test_profile_format_keeps_secrets_separate_from_settings(self):
        for field in ('wifi_password', 'mqtt_password', 'api_clients'):
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, 'unsupported configuration profile setting'
            ):
                configuration_profiles.normalize_profile({
                    'name': 'Unsafe', 'settings': {field: 'secret'},
                })

        normalized = configuration_profiles.normalize_profile({
            'name': 'Secure', 'settings': {'release_channel': 'beta'},
            'secrets': {
                'wifi_password': 'correct horse battery staple',
                'mqtt_password': 'broker-secret',
            },
        })
        self.assertEqual(normalized['secrets']['mqtt_password'], 'broker-secret')

    def test_profile_can_select_one_setting_and_network_values(self):
        normalized = configuration_profiles.normalize_profile({
            'name': 'Network',
            'settings': {
                'wifi_ssid': 'Production WiFi',
                'wifi_dhcp': False,
                'wifi_ip_address': '192.168.1.50',
                'wifi_subnet_mask': '255.255.255.0',
                'wifi_gateway': '192.168.1.1',
                'wifi_dns_server': '192.168.1.1',
            },
        })
        self.assertEqual(normalized['settings']['wifi_ssid'], 'Production WiFi')
        self.assertFalse(normalized['settings']['wifi_dhcp'])
        self.assertEqual(
            configuration_profiles.normalize_profile({
                'name': 'Syslog only',
                'settings': {'syslog_enabled': True},
            })['settings'],
            {'syslog_enabled': True},
        )

    def test_network_profile_starts_a_rollback_trial(self):
        credentials = Credentials()
        service = ConfigurationProfileService(
            credentials, Timezone(), Health(), lambda _reason: None
        )

        result = service.apply({
            'name': 'Wi-Fi', 'settings': {'wifi_ssid': 'Production WiFi'},
        }, 'Management')

        self.assertTrue(credentials.network_trial)
        self.assertTrue(result['network_trial_pending'])

    def test_profile_matches_device_runtime_limits(self):
        with self.assertRaisesRegex(ValueError, 'log_buffer_lines'):
            configuration_profiles.normalize_profile({
                'name': 'Too many logs',
                'settings': {'log_buffer_lines': 501},
            })
        with self.assertRaisesRegex(ValueError, 'syslog_transport'):
            configuration_profiles.normalize_profile({
                'name': 'TCP syslog',
                'settings': {'syslog_transport': 'tcp'},
            })

    def test_profile_rejects_invalid_update_schedule(self):
        with self.assertRaisesRegex(ValueError, 'release_check_time'):
            configuration_profiles.normalize_profile({
                'name': 'Invalid',
                'settings': {
                    'release_channel': 'alpha',
                    'release_check_schedule': 'weekly',
                    'release_check_time': '25:00',
                },
            })


if __name__ == '__main__':
    unittest.main()
