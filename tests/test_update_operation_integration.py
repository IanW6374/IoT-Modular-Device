"""Offline integration: signed admission and read-only API, no device I/O."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import fleet_management
import update_security
from api_contracts import APIRequest
from device_api import DeviceAPI
from update_operations import UpdateOperations


class UpdateOperationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.private_key = bytes(range(1, 33))
        self.key = self.root / 'key'
        self.key.write_bytes(update_security.public_key_bytes(self.private_key))
        self.ops = UpdateOperations('device', str(self.root / 'operations'))

    def service(self):
        return fleet_management.FleetService('device', state_path=str(self.root / 'fleet'),
            key_path=str(self.key), now=lambda: 2000000000,
            update_operations=self.ops)

    def policy(self, sequence=1):
        policy = {'format_version': 2, 'target_board': 'esp32-s3', 'policy_sequence': sequence,
            'issued_at': 1999999900, 'not_before': 1999999990, 'expires_at': 2000000100,
            'target_device': 'device', 'target_cohort': '',
            'maintenance': {'weekdays': list(range(7)), 'start_minute': 0, 'duration_minutes': 1440},
            'updates': {'channel': 'alpha', 'automatic_download': True,
                'automatic_activation': True, 'maximum_consecutive_failures': 2},
            'telemetry': {'enabled': True, 'minimum_interval_s': 10, 'severities': ['error']},
            'commands': [{'id': '%032x' % (sequence*10+i), 'action': action,
                         'release_sequence': 2828, 'release_type': 'universal'}
                        for i, action in enumerate(['check-update', 'download-update', 'activate-update'])],
            'signature_scheme': update_security.SIGNATURE_SCHEME}
        policy['signature'] = update_security.sign_manifest('fleet-policy', policy, self.private_key)
        return policy

    def test_verified_admission_has_stable_identity_and_only_then_executable_commands(self):
        service = self.service()
        policy = self.policy()
        service.apply_policy(policy)
        self.assertEqual(self.ops.active()['id'], policy['commands'][0]['id'])
        self.assertEqual(self.ops.active()['state'], 'accepted')
        self.assertEqual(len(service.pending_commands()), 3)

    def test_signature_or_identity_rejection_reserves_no_storage_or_operation(self):
        service = self.service()
        for field, value in (('target_device', 'other-device'), ('signature', '0'*128)):
            policy = self.policy()
            policy[field] = value
            with self.assertRaises(ValueError): service.apply_policy(policy)
            self.assertFalse(self.ops.loaded)
            self.assertEqual(self.ops.state['records'], [])

    def test_storage_admission_failure_leaves_policy_and_commands_unchanged(self):
        service = self.service()
        with mock.patch.object(self.ops, '_commit', side_effect=OSError('full')):
            with self.assertRaises(OSError): service.apply_policy(self.policy())
        self.assertIsNone(service.state['policy'])
        self.assertEqual(service.state['policy_sequence'], 0)
        self.assertEqual(service.pending_commands(), [])

    def test_policy_commit_failure_cannot_execute_prepared_commands(self):
        service = self.service()
        with mock.patch.object(service, '_save', side_effect=OSError('full')):
            with self.assertRaises(OSError): service.apply_policy(self.policy())
        self.assertEqual(self.ops.active()['state'], 'prepared')
        self.assertEqual(service.pending_commands(), [])
        recovered = self.service()
        self.ops.recover_admission(recovered.state.get('policy'))
        self.assertIsNone(self.ops.active())

    def test_terminal_or_cancelling_operation_suppresses_captured_policy_commands(self):
        service = self.service()
        service.apply_policy(self.policy())
        self.ops.transition('cancelling')
        self.assertEqual(service.pending_commands(), [])
        self.ops.transition('cancelled')
        self.assertEqual(service.pending_commands(), [])

    def test_snapshot_api_uses_fleet_read_auth_and_does_not_replay_a_mutation(self):
        service = self.service()
        service.apply_policy(self.policy())
        scopes = []
        registry = SimpleNamespace(authenticate=lambda identity, scope:
                                   (scopes.append(scope) or {'fingerprint': 'client', 'label': 'Test'}))
        api = DeviceAPI(SimpleNamespace(catalog=lambda: []), None, registry, lambda: {},
                        fleet=service, update_status_getter=lambda: {'device_id': 'device'})
        with mock.patch.object(self.ops, '_commit', side_effect=AssertionError('Snapshot wrote journal')):
            response = api.handle(APIRequest('GET', '/api/v3/fleet/update-operations/' + self.ops.active()['id']))
        self.assertEqual(response.status, 200)
        self.assertTrue(all(scope == 'fleet:read' for scope in scopes))
        self.assertEqual(response.payload['update_operation']['state'], 'accepted')
        self.assertNotIn('signature', json.dumps(response.payload))

    def test_retained_operation_query_is_not_implicit_success_when_missing(self):
        service = self.service()
        service.apply_policy(self.policy())
        registry = SimpleNamespace(authenticate=lambda *_: {'fingerprint': 'client', 'label': 'Test'})
        api = DeviceAPI(SimpleNamespace(catalog=lambda: []), None, registry, lambda: {}, fleet=service)
        response = api.handle(APIRequest('GET', '/api/v3/fleet/update-operations/' + 'f'*32))
        self.assertEqual(response.status, 404)

