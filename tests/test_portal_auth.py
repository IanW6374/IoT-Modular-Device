import asyncio
import unittest

import credential_store
import portal_auth


class PortalAuthTests(unittest.TestCase):
    def setUp(self):
        credential_store._memory_values.clear()
        config = credential_store.build_configuration({
            'device_name': 'Controller', 'wifi_ssid': 'network',
            'wifi_password': 'network-password', 'mqtt_server': 'mqtt.local',
            'mqtt_port': 8883, 'mqtt_ssl': True, 'portal_username': 'admin',
            'recovery_ap_password': 'Recovery-Access-47!River',
            'channel': 'stable',
        }, 'Administrator-Cedar-47!River', 'Recovery-Console-82!Stone')
        config['provisioned'] = True
        credential_store.save(config)

    def tearDown(self):
        credential_store._memory_values.clear()

    def test_add_authenticate_update_and_remove_user(self):
        portal_auth.add_user('viewer', 'Viewer-Cedar-47!River', 'viewer')
        identity = asyncio.run(portal_auth.authenticate(
            'viewer', 'Viewer-Cedar-47!River'
        ))
        self.assertEqual(identity['username'], 'viewer')
        self.assertEqual(identity['role'], 'viewer')
        self.assertEqual(identity['max_retries'], 5)
        self.assertEqual(identity['session_timeout_s'], 3600)
        self.assertFalse(identity['password_change_required'])

        portal_auth.update_user('viewer', role='operator', enabled=False)
        self.assertIsNone(asyncio.run(portal_auth.authenticate(
            'viewer', 'Viewer-Cedar-47!River'
        )))
        self.assertTrue(portal_auth.remove_user('viewer'))

    def test_user_lockout_timeout_and_forced_password_change_are_persistent(self):
        portal_auth.add_user(
            'operator', 'Operator-Cedar-47!River', 'operator',
            max_retries=2, session_timeout_s=900,
            password_change_required=True
        )
        first = asyncio.run(portal_auth.authenticate(
            'operator', 'Operator-Cedar-47!River'
        ))
        self.assertEqual(first['session_timeout_s'], 900)
        self.assertTrue(first['password_change_required'])

        self.assertIsNone(asyncio.run(portal_auth.authenticate('operator', 'wrong')))
        self.assertIsNone(asyncio.run(portal_auth.authenticate('operator', 'wrong')))
        locked = next(
            user for user in portal_auth.list_users()
            if user['username'] == 'operator'
        )
        self.assertEqual(locked['failed_attempts'], 2)
        self.assertTrue(locked['locked'])
        self.assertIsNone(asyncio.run(portal_auth.authenticate(
            'operator', 'Operator-Cedar-47!River'
        )))

        portal_auth.update_user('operator', reset_lockout=True)
        self.assertIsNotNone(asyncio.run(portal_auth.authenticate(
            'operator', 'Operator-Cedar-47!River'
        )))
        changed = portal_auth.update_user(
            'operator', password='Operator-Ash-82!Stone'
        )
        self.assertFalse(changed['locked'])
        self.assertFalse(changed['password_change_required'])

    def test_user_form_helpers_apply_security_policy(self):
        added = portal_auth.add_user_from_form({
            'username': 'form-user', 'password': 'Viewer-Cedar-47!River',
            'role': 'viewer', 'max_retries': '3',
            'session_timeout_minutes': '15',
            'password_change_required': 'true',
        })
        self.assertEqual(added['max_retries'], 3)
        self.assertEqual(added['session_timeout_s'], 900)
        self.assertTrue(added['password_change_required'])
        self.assertTrue(added['enabled'])
        disabled = portal_auth.add_user_from_form({
            'username': 'disabled-user', 'password': 'Viewer-Maple-83!Lake',
            'role': 'viewer', 'enabled': 'false',
        })
        self.assertFalse(disabled['enabled'])
        updated = portal_auth.update_user_from_form({
            'username': 'form-user', 'new_username': 'renamed-user',
            'role': 'operator', 'enabled': 'true', 'max_retries': '4',
            'session_timeout_minutes': '30',
        })
        self.assertEqual(updated['previous_username'], 'form-user')
        self.assertEqual(updated['username'], 'renamed-user')
        self.assertEqual(updated['session_timeout_s'], 1800)
        self.assertFalse(updated['password_change_required'])

    def test_cannot_remove_or_disable_last_administrator(self):
        with self.assertRaisesRegex(ValueError, 'administrator'):
            portal_auth.update_user('admin', enabled=False)
        with self.assertRaisesRegex(ValueError, 'administrator'):
            portal_auth.remove_user('admin')

    def test_administrator_username_can_be_changed_from_user_management(self):
        result = portal_auth.update_user('admin', new_username='portal-admin')
        self.assertEqual(result['username'], 'portal-admin')
        config = credential_store.load(require_provisioned=True)
        self.assertEqual(config['portal']['username'], 'portal-admin')
        self.assertIsNone(asyncio.run(portal_auth.authenticate(
            'admin', 'Administrator-Cedar-47!River'
        )))
        self.assertEqual(
            asyncio.run(portal_auth.authenticate(
                'portal-admin', 'Administrator-Cedar-47!River'
            ))['role'],
            'administrator'
        )

    def test_route_roles(self):
        self.assertEqual(portal_auth.required_role('GET', '/'), 'viewer')
        self.assertEqual(portal_auth.required_role('POST', '/activate-update'), 'operator')
        self.assertEqual(portal_auth.required_role('GET', '/certificates'), 'administrator')
        self.assertEqual(portal_auth.required_role('GET', '/api/restart-required'), 'viewer')
        self.assertEqual(portal_auth.required_role('POST', '/restart-device'), 'administrator')
        self.assertEqual(portal_auth.required_role('POST', '/shutdown-device'), 'administrator')
        self.assertEqual(portal_auth.required_role('POST', '/logout'), 'viewer')
        self.assertTrue(portal_auth.role_allows('administrator', 'operator'))
        self.assertFalse(portal_auth.role_allows('viewer', 'operator'))


if __name__ == '__main__':
    unittest.main()
