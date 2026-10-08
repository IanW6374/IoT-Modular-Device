import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import api_security
import certificate_manager
import certificate_codec
import configuration_profiles
import device_api
import http_support
from api_contracts import APIRequest, APIResponse
from device_api import DeviceAPI
from device_api_inventory import DeviceInventory
from feature_flags import FeatureFlags
from runtime_health import HealthHistory
from api_operations import OperationJournal
from api_operation_fixtures import MemoryNamespace


def client_certificate(common_name='automation-client.local'):
    original_time = certificate_codec.time

    class FixedTime:
        @staticmethod
        def localtime():
            return (2026, 1, 1, 0, 0, 0, 0, 1)

    certificate_codec.time = FixedTime()
    try:
        return certificate_manager._self_signed_certificate(
            bytes(range(1, 33)), common_name
        )
    finally:
        certificate_codec.time = original_time


class FakeBroker:
    def __init__(self):
        self.commands = []

    def catalog(self):
        return [{'uuid': '0001', 'name': 'Boiler'}]

    def state(self, uuid):
        if uuid != '0001':
            raise KeyError(uuid)
        return {'temperature': 55}

    def diagnostics(self, uuid):
        return {'last_ok': True}

    def submit(self, uuid, command, source, identity):
        self.commands.append((uuid, command, source, identity))
        return {'id': command.get('request_id', 'generated'), 'status': 'queued'}

    def operation(self, operation_id):
        return {'id': operation_id, 'status': 'complete'} if operation_id == 'known' else None


class DeviceAPITests(unittest.TestCase):
    def test_inventory_bounds_release_qualification_projection(self):
        inventory = DeviceInventory({
            'qualification': {
                'available': True,
                'summary': 'In progress',
                'evidence': {
                    'promotion_ready': False,
                    'gates': [
                        {'name': 'x' * 80, 'status': 'in-progress'}
                        for unused in range(20)
                    ],
                },
            },
            'qualification_observation': {
                'health_state': 'healthy', 'storage_free_bytes': 1024,
            },
        })
        value = inventory.info()
        self.assertEqual(value['release_qualification']['summary'], 'In progress')
        self.assertEqual(len(value['release_qualification']['gates']), 16)
        self.assertEqual(
            len(value['release_qualification']['gates'][0]['name']), 32
        )
        self.assertEqual(
            value['qualification_observation']['storage_free_bytes'], 1024
        )

    def test_configuration_reports_automatic_update_schedule(self):
        inventory = DeviceInventory({
            'release_check_schedule': 'weekly',
            'release_check_time': '02:30',
            'release_check_weekday': 6,
            'release_auto_download': True,
            'release_auto_activate': True,
        })

        schedule = inventory.configuration()['automatic_updates']

        self.assertEqual(schedule['schedule'], 'weekly')
        self.assertEqual(schedule['time'], '02:30')
        self.assertEqual(schedule['weekday'], 6)
        self.assertTrue(schedule['download'])
        self.assertTrue(schedule['activate'])

    def test_v1_namespace_is_not_exposed_by_clean_seed_runtime(self):
        self.registry.enrol(self.cert, 'reader', ('read',))
        status, body = self.api.dispatch(
            'GET', '/api/v1/modules', b'', self.cert
        )
        self.assertEqual(status, 404)
        self.assertEqual(body['error'], 'endpoint not found')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        registry_path = str(Path(self.temp.name) / 'clients.json')
        self.registry = api_security.ClientRegistry(registry_path)
        self.cert = client_certificate()
        self.health = HealthHistory(str(Path(self.temp.name) / 'health.json'))
        self.broker = FakeBroker()
        self.operation_storage = MemoryNamespace()
        self.operations = OperationJournal(lambda: self.operation_storage,
            str(Path(self.temp.name) / 'operations'))
        self.api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'}, operations=self.operations
        )

    def tearDown(self):
        self.temp.cleanup()

    def mutation(self, key='1.0123456789abcdef', body=b'{}'):
        return APIRequest('POST', '/api/v3/configuration/restart', body, self.cert,
            headers={'Idempotency-Key': key})

    def test_mutation_replay_after_restart_never_calls_device_again(self):
        self.registry.enrol(self.cert, 'writer', ('read', 'configuration:write'))
        self.api.configuration_restarter = mock.Mock(return_value={'scheduled': True})
        first = self.api.handle(self.mutation())
        self.assertEqual(first.status, 202)
        self.api.operations = OperationJournal(lambda: self.operation_storage,
            str(Path(self.temp.name) / 'operations'), boot_id='new-boot')
        second = self.api.handle(self.mutation())
        self.assertEqual(second.status, 202)
        self.assertEqual(first.payload['operation']['id'], second.payload['operation']['id'])
        self.api.configuration_restarter.assert_called_once()
        self.assertEqual(second.payload['operation']['completion_scope'], 'request')

    def test_mutation_without_key_or_durable_storage_never_executes(self):
        self.registry.enrol(self.cert, 'writer', ('configuration:write',))
        self.api.configuration_restarter = mock.Mock()
        request = self.mutation(); request.headers = {}
        self.assertEqual(self.api.handle(request).status, 400)
        self.api.operations = None
        self.assertEqual(self.api.handle(self.mutation()).status, 503)
        self.api.configuration_restarter.assert_not_called()

    def test_authorization_is_rechecked_before_replaying_a_result(self):
        self.registry.enrol(self.cert, 'writer', ('read', 'configuration:write'))
        self.api.configuration_restarter = mock.Mock(return_value={'scheduled': True})
        self.assertEqual(self.api.handle(self.mutation()).status, 202)
        self.registry.enrol(self.cert, 'reader', ('read',))
        self.assertEqual(self.api.handle(self.mutation()).status, 403)
        self.api.configuration_restarter.assert_called_once()

    def test_unavailable_journal_does_not_fall_back_to_unscoped_broker_history(self):
        self.registry.enrol(self.cert, 'reader', ('read',))
        self.api.operations = None
        self.broker.operation = mock.Mock(return_value={'id': 'other-client'})
        for path in ('/api/v3/operations', '/api/v3/operations/other-client',
                     '/api/v3/operations/other-client/result'):
            with self.subTest(path=path):
                self.assertEqual(self.api.handle(APIRequest('GET', path, identity=self.cert)).status, 503)
        self.broker.operation.assert_not_called()

    def test_operation_reservation_failure_prevents_callback(self):
        self.registry.enrol(self.cert, 'writer', ('configuration:write',))
        self.api.configuration_restarter = mock.Mock()
        self.operation_storage.fail = True
        self.assertEqual(self.api.handle(self.mutation()).status, 503)
        self.api.configuration_restarter.assert_not_called()

    def test_async_module_completion_is_durable_and_client_bound(self):
        self.registry.enrol(self.cert, 'writer', ('read', 'write'))
        response = self.api.handle(APIRequest('POST', '/api/v3/modules/0001/commands',
            b'{"request_id":"spoofed"}', self.cert,
            headers={'Idempotency-Key': '1.0123456789abcdef'}))
        operation = response.payload['operation']
        identifier = operation['id']
        self.assertEqual(operation['status'], 'queued')
        self.assertEqual(self.broker.commands[0][1]['request_id'], identifier)
        record = self.operations.state['records'][0]
        event = {'id': identifier, 'status': 'complete', 'source': 'mqtt', 'identity': record['client'][:16]}
        self.api._operation_completed(event)
        self.assertEqual(self.operations.operation(identifier, record['client'])['status'], 'queued')
        event['source'] = 'api'
        self.api._operation_completed(event)
        self.assertEqual(self.operations.operation(identifier, record['client'])['status'], 'complete')
        self.api.operations = OperationJournal(lambda: self.operation_storage,
            str(Path(self.temp.name) / 'operations'), boot_id='new-boot')
        result = self.api.handle(APIRequest('GET', '/api/v3/operations/' + identifier + '/result', identity=self.cert))
        self.assertEqual(result.status, 200)
        self.assertEqual(result.payload['status'], 'complete')

    def test_commit_failure_after_callback_reports_uncertain_and_never_repeats(self):
        self.registry.enrol(self.cert, 'writer', ('configuration:write',))
        callback = mock.Mock(return_value={'scheduled': True})
        self.api.configuration_restarter = callback
        with mock.patch.object(self.operations, 'finish', side_effect=OSError('result storage failed')):
            response = self.api.handle(self.mutation())
        self.assertEqual(response.status, 503)
        retry = self.api.handle(self.mutation())
        self.assertEqual(retry.status, 409)
        callback.assert_called_once()

    def test_v3_discovery_is_scoped_and_advertises_real_capabilities(self):
        denied = self.api.handle(APIRequest('GET', '/api/v3', identity=self.cert))
        self.assertEqual(denied.status, 403)
        self.assertEqual(denied.payload['error']['code'], 'permission_denied')
        self.registry.enrol(self.cert, 'reader', ('read',))
        response = self.api.handle(APIRequest('GET', '/api/v3', identity=self.cert))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.payload['api_version'], 3)
        self.assertFalse(response.payload['capabilities']['encrypted_backups'])
        self.assertTrue(response.payload['capabilities']['persistent_idempotency'])
        self.assertEqual(response.payload['limits']['request_body_bytes'], 8192)
        self.assertEqual(response.payload['limits']['restore_preview_body_bytes'], 384 * 1024)

    def test_v2_retirement_never_executes_a_command(self):
        self.registry.enrol(self.cert, 'controller', ('read', 'write'))
        for method, path in (('GET', '/api/v2'), ('GET', '/api/v2/device'),
                             ('POST', '/api/v2/modules/0001/commands')):
            response = self.api.handle(APIRequest(method, path, b'{}', self.cert))
            self.assertEqual(response.status, 410)
            self.assertEqual(response.payload['error']['code'], 'unsupported_api_version')
            self.assertFalse(response.payload['error']['retryable'])
        self.assertEqual(self.broker.commands, [])

    def test_v3_wire_errors_and_successes_have_version(self):
        self.registry.enrol(self.cert, 'controller', ('read', 'write'))
        response = self.api.handle(APIRequest('GET', '/api/v3/modules/0001/state', identity=self.cert))
        self.assertEqual(response.payload['api_version'], 3)
        response = self.api.handle(APIRequest('POST', '/api/v3/modules/0001/commands', b'{', self.cert,
            headers={'Idempotency-Key': '1.0123456789abcdef'}))
        self.assertEqual(response.status, 400)
        self.assertEqual(response.payload['error']['code'], 'invalid_request')
        response = self.api.handle(APIRequest('GET', '/api/v3/missing', identity=self.cert))
        self.assertEqual(response.status, 404)
        self.assertEqual(response.payload['error']['code'], 'not_found')
        self.registry.revoke(self.registry.list_clients()[0]['fingerprint'])
        response = self.api.handle(APIRequest('GET', '/api/v3', identity=self.cert))
        self.assertEqual(response.status, 403)

    def test_read_scoped_client_can_read_but_not_write(self):
        record = self.registry.enrol(self.cert, 'reader', ('read',))
        self.assertEqual(len(record['fingerprint']), 64)
        listed = self.registry.list_clients()[0]
        self.assertIn(listed['expiry_level'], ('ok', 'unknown'))
        self.assertIn('days_remaining', listed)

        status, payload = self.api.dispatch(
            'GET', '/api/v3/modules/0001/state', b'', self.cert
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload['state']['temperature'], 55)

        with self.assertRaisesRegex(PermissionError, 'write scope'):
            self.api.dispatch(
                'POST', '/api/v3/modules/0001/commands', b'{"value":1}', self.cert
            )

    def test_write_client_submits_same_json_command_contract(self):
        self.registry.enrol(self.cert, 'controller', ('read', 'write'))

        status, operation = self.api.dispatch(
            'POST', '/api/v3/modules/0001/commands',
            b'{"request_id":"abc","operation":"write","value":20}',
            self.cert
        )

        self.assertEqual(status, 202)
        self.assertEqual(operation['id'], 'abc')
        self.assertEqual(self.broker.commands[0][1]['operation'], 'write')
        self.assertEqual(self.broker.commands[0][2], 'api')

    def test_configuration_profiles_use_dedicated_scope_and_are_validated(self):
        applied = []
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            configuration_profile_applier=lambda value, actor:
                applied.append((configuration_profiles.normalize_profile(value), actor)) or {
                    'name': value['name'], 'restart_required': True,
                },
        )
        self.registry.enrol(self.cert, 'fleet manager', ('configuration:write',))
        profile = {
            'format_version': 1, 'name': 'Standard',
            'settings': {
                'timezone_name': 'Europe/London',
                'ntp_servers': ['pool.ntp.org'],
                'ha_discovery': True,
                'mqtt_qos': 1,
            },
        }
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/profile',
            json.dumps(profile).encode(), self.cert,
        )
        self.assertEqual(status, 202)
        self.assertTrue(payload['profile']['restart_required'])
        self.assertEqual(applied[0][0]['name'], 'Standard')
        self.assertEqual(applied[0][1], 'fleet manager')

    def test_generic_write_scope_cannot_apply_configuration_profile(self):
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            configuration_profile_applier=lambda value, actor: value,
        )
        self.registry.enrol(self.cert, 'controller', ('write',))
        with self.assertRaisesRegex(PermissionError, 'configuration:write'):
            api.dispatch(
                'POST', '/api/v3/configuration/profile',
                b'{"name":"Standard","settings":{"ha_discovery":true}}',
                self.cert,
            )

    def test_configuration_scope_manages_complete_backup_restore(self):
        calls = []
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            configuration_backup=lambda password:
                calls.append(('backup', password)) or {'format': 'encrypted'},
            configuration_restore_preview=lambda request:
                calls.append(('preview', request)) or {'token': 'restore-token'},
            configuration_restore_apply=lambda token:
                calls.append(('apply', token)) or 'restart required',
        )
        self.registry.enrol(self.cert, 'fleet manager', ('configuration:write',))

        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/backups',
            b'{"salt":"00000000000000000000000000000000",'
            b'"derived_key":"11111111111111111111111111111111"}', self.cert,
        )
        self.assertEqual((status, payload['backup']['format']), (201, 'encrypted'))
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/backups/preview',
            b'{"backup":{"format":"encrypted"},'
            b'"derived_key":"11111111111111111111111111111111"}',
            self.cert,
        )
        self.assertEqual((status, payload['preview']['token']), (200, 'restore-token'))
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/backups/apply',
            b'{"token":"restore-token"}', self.cert,
        )
        self.assertEqual((status, payload['restore']), (202, 'restart required'))
        self.assertEqual(calls[0], (
            'backup', {
                'salt': '00000000000000000000000000000000',
                'derived_key': '11111111111111111111111111111111',
            }
        ))
        self.assertEqual(calls[-1], ('apply', 'restore-token'))

    def test_legacy_managed_backup_is_rejected_before_device_key_derivation(self):
        backup = mock.Mock()
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'}, configuration_backup=backup,
        )
        self.registry.enrol(self.cert, 'fleet manager', ('configuration:write',))

        with self.assertRaisesRegex(ValueError, 'Management 2.7.3'):
            api.dispatch(
                'POST', '/api/v3/configuration/backups',
                b'{"password":"legacy-password"}', self.cert,
            )

        backup.assert_not_called()

    def test_only_backup_preview_receives_large_envelope_body_limit(self):
        configured = 8192

        self.assertEqual(
            device_api.request_body_limit(
                '/api/v3/configuration/backups/preview', configured
            ),
            384 * 1024,
        )
        self.assertEqual(
            device_api.request_body_limit(
                '/api/v3/configuration/backups/preview?source=management',
                configured,
            ),
            384 * 1024,
        )
        self.assertEqual(
            device_api.request_body_limit(
                '/api/v3/configuration/profile', configured
            ),
            configured,
        )

    def test_configuration_scope_can_stage_and_apply_certificates(self):
        staged = []
        restarted = []
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            certificate_stager=lambda kind, payload:
                staged.append((kind, payload)) or {'staged': True},
            certificate_applier=lambda: {'restart': True},
            network_confirmer=lambda: True,
            configuration_restarter=lambda:
                restarted.append(True) or {'message': 'restarting'},
        )
        self.registry.enrol(self.cert, 'fleet manager', ('configuration:write',))
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/certificates/mqtt-ca',
            b'certificate-bytes', self.cert,
        )
        self.assertEqual(status, 202)
        self.assertEqual(staged, [('mqtt-ca', b'certificate-bytes')])
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/certificates/apply', b'{}', self.cert,
        )
        self.assertTrue(payload['certificates']['restart'])
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/network/confirm', b'{}', self.cert,
        )
        self.assertTrue(payload['confirmed'])
        status, payload = api.dispatch(
            'POST', '/api/v3/configuration/restart', b'{}', self.cert,
        )
        self.assertEqual(status, 202)
        self.assertEqual(restarted, [True])
        self.assertEqual(payload['restart']['message'], 'restarting')

    def test_configuration_profile_rejects_secrets_and_unknown_settings(self):
        with self.assertRaisesRegex(ValueError, 'unsupported.*wifi_password'):
            configuration_profiles.normalize_profile({
                'name': 'Unsafe', 'settings': {'wifi_password': 'secret'},
            })
        with self.assertRaisesRegex(ValueError, '1 to 4'):
            configuration_profiles.normalize_profile({
                'name': 'Invalid', 'settings': {'ntp_servers': []},
            })

    def test_qualification_endpoints_use_dedicated_scopes(self):
        events = []
        scenarios = []
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            qualification_getter=lambda: {'summary': 'In progress'},
            qualification_event=lambda value, actor:
                events.append((value, actor)) or value,
            qualification_scenario=lambda value, actor:
                scenarios.append((value, actor)) or value,
        )
        self.registry.enrol(self.cert, 'HIL rig', (
            'read', 'qualification:write', 'qualification:execute'
        ))
        status, payload = api.dispatch(
            'GET', '/api/v3/qualification', b'', self.cert
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload['qualification']['summary'], 'In progress')
        status, payload = api.dispatch(
            'POST', '/api/v3/qualification/events',
            b'{"gate":"watchdog-recovery"}', self.cert
        )
        self.assertEqual(status, 202)
        self.assertEqual(events[0][1], 'HIL rig')
        status, payload = api.dispatch(
            'POST', '/api/v3/qualification/scenarios/watchdog-recovery',
            b'{"run_id":"hil-1"}', self.cert
        )
        self.assertEqual(status, 202)
        self.assertEqual(scenarios[0][0]['scenario'], 'watchdog-recovery')

    def test_generic_write_scope_cannot_record_qualification(self):
        self.registry.enrol(self.cert, 'controller', ('read', 'write'))
        with self.assertRaisesRegex(PermissionError, 'qualification:write'):
            self.api.dispatch(
                'POST', '/api/v3/qualification/events', b'{}', self.cert
            )

    def test_connection_and_commands_are_audit_but_requests_are_debug(self):
        logs = []
        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            lambda *args: logs.append(args)
        )
        self.registry.enrol(self.cert, 'controller', ('read', 'write'))

        api.connection_opened(self.cert, '192.0.2.10')
        api.dispatch('GET', '/api/v3/modules', b'', self.cert)
        api.dispatch(
            'POST', '/api/v3/modules/0001/commands',
            b'{"request_id":"audit-1","operation":"write"}', self.cert
        )

        connection = next(item for item in logs if item[1] == 'Connection')
        request = next(item for item in logs if item[1] == 'Request')
        command = next(item for item in logs if item[1] == 'Module command')
        self.assertTrue(connection[2]['audit'])
        self.assertIn('192.0.2.10', connection[2]['log'])
        self.assertEqual(request[3], 'DEBUG')
        self.assertNotIn('audit', request[2])
        self.assertTrue(command[2]['audit'])

    def test_unenrolled_certificate_is_rejected(self):
        with self.assertRaisesRegex(PermissionError, 'not enrolled'):
            self.api.dispatch('GET', '/api/v3/device/inventory', b'', self.cert)

    def test_revoked_certificate_is_rejected(self):
        record = self.registry.enrol(self.cert, 'reader', ('read',))
        self.assertTrue(self.registry.revoke(record['fingerprint']))
        with self.assertRaises(PermissionError):
            self.api.dispatch('GET', '/api/v3/device/inventory', b'', self.cert)

    def test_cached_connection_identity_honours_immediate_revocation(self):
        record = self.registry.enrol(self.cert, 'reader', ('read',))
        client = self.api.connection_opened(self.cert)

        status, _payload = self.api.dispatch(
            'GET', '/api/v3/device/inventory', b'', self.cert,
            authenticated_client=client
        )
        self.assertEqual(status, 200)

        self.assertTrue(self.registry.revoke(record['fingerprint']))
        with self.assertRaises(PermissionError):
            self.api.dispatch(
                'GET', '/api/v3/device/inventory', b'', self.cert,
                authenticated_client=client
            )

    def test_registry_creates_nested_absolute_directory(self):
        path = Path(self.temp.name) / 'nested' / 'certs' / 'clients.json'
        registry = api_security.ClientRegistry(str(path))

        registry.enrol(self.cert, 'reader', ('read',))

        self.assertTrue(path.is_file())

    def test_registry_updates_existing_client_scopes_without_duplicate(self):
        record = self.registry.enrol(
            self.cert, 'combined automation', ('read', 'write')
        )

        updated = self.registry.update_scopes(record['fingerprint'], (
            'read', 'write', 'qualification:write', 'qualification:execute'
        ))

        self.assertEqual(len(self.registry.list_clients()), 1)
        self.assertEqual(updated['label'], 'combined automation')
        self.assertEqual(updated['subject'], record['subject'])
        self.assertEqual(updated['scopes'], [
            'qualification:execute', 'qualification:write', 'read', 'write'
        ])

    def test_registry_rejects_empty_unknown_and_missing_scope_updates(self):
        record = self.registry.enrol(self.cert, 'reader', ('read',))

        with self.assertRaisesRegex(ValueError, 'at least one scope'):
            self.registry.update_scopes(record['fingerprint'], ())
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            self.registry.update_scopes(record['fingerprint'], ('admin',))
        with self.assertRaisesRegex(ValueError, 'not found'):
            self.registry.update_scopes('00' * 32, ('read',))

        self.assertEqual(self.registry.list_clients()[0]['scopes'], ['read'])

    def test_staged_client_uses_selected_permission_preset(self):
        directory = Path(self.temp.name) / 'staged'
        directory.mkdir()
        certificate_path = directory / ('.api-client-stage-' + ('a' * 24) + '.der')
        staged_path = Path(str(certificate_path) + '.manual')
        staged_path.write_bytes(self.cert)

        api_security.stage_client_scopes(
            str(certificate_path), 'api-client-cert',
            'fleet:read,fleet:write,configuration:write'
        )
        stages = api_security.staged_clients(
            str(directory), [item.name for item in directory.iterdir()],
            certificate_manager.decode_certificate
        )

        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0][2], (
            'configuration:write', 'fleet:read', 'fleet:write'
        ))

    def test_custom_client_scope_selection_rejects_unknown_permissions(self):
        certificate_path = str(Path(self.temp.name) / 'client.der')

        with self.assertRaisesRegex(ValueError, 'unsupported'):
            api_security.stage_client_scopes(
                certificate_path, 'api-client-cert', 'read,administrator'
            )

    def test_v1_registry_is_rejected_by_clean_seed_runtime(self):
        path = Path(self.temp.name) / 'legacy-clients.json'
        fingerprint = api_security.certificate_fingerprint(self.cert)
        path.write_text(json.dumps({
            'format_version': 1,
            'clients': [{
                'fingerprint': fingerprint,
                'label': 'v1 automation',
                'scopes': ['read', 'write'],
                'subject': 'automation-client.local',
                'issuer': 'automation-client.local',
                'not_after': '',
            }],
        }))
        registry = api_security.ClientRegistry(str(path))

        with self.assertRaisesRegex(ValueError, 'invalid format'):
            registry.list_clients()

    def test_invalid_module_uuid_returns_json_404(self):
        self.registry.enrol(self.cert, 'reader', ('read',))

        status, payload = self.api.dispatch(
            'GET', '/api/v3/modules/ffff/state', b'', self.cert
        )

        self.assertEqual(status, 404)
        self.assertEqual(payload['module'], 'ffff')
        self.assertEqual(self.health.snapshot()['counters']['api_requests'], 1)
        self.assertEqual(self.health.snapshot()['counters']['api_failures'], 1)
        self.assertEqual(self.health.snapshot()['events'][-1]['kind'], 'api_not_found')

    def test_multiple_independent_api_ca_trusts_are_stored(self):
        store = api_security.CATrustStore(
            str(Path(self.temp.name) / 'trust'), maximum=4
        )
        first = client_certificate('first-ca.local')
        second = client_certificate('second-ca.local')

        store.add(first)
        store.add(second)

        self.assertEqual(len(store.paths()), 2)
        self.assertEqual(len(store.list()), 2)

    def test_server_completes_deferred_tls_handshake_before_reading_peer_certificate(self):
        self.registry.enrol(self.cert, 'reader', ('read',))

        class TLSStream:
            def __init__(stream_self):
                stream_self.handshake_complete = False

            def getpeercert(stream_self, binary_form=False):
                if not stream_self.handshake_complete:
                    raise RuntimeError('certificate inspected before TLS handshake')
                return self.cert

        class Reader:
            def __init__(stream_self):
                stream_self.s = TLSStream()
                stream_self.data = (
                    b'GET /api/v3/modules HTTP/1.1\r\n'
                    b'Connection: close\r\n\r\n'
                )

            async def read(stream_self, size):
                stream_self.s.handshake_complete = True
                value, stream_self.data = (
                    stream_self.data[:size], stream_self.data[size:]
                )
                return value

        class Writer:
            def __init__(stream_self):
                stream_self.payload = bytearray()

            def write(stream_self, payload):
                stream_self.payload.extend(payload)

            async def drain(stream_self):
                pass

            def close(stream_self):
                pass

            async def wait_closed(stream_self):
                pass

        async def exercise():
            captured = {}

            async def capture_server(handler, *_args, **_kwargs):
                captured['handler'] = handler
                return object()

            with mock.patch.object(device_api, 'make_mtls_context', return_value=object()), \
                    mock.patch.object(device_api.asyncio, 'start_server', side_effect=capture_server):
                await device_api.start_device_api({
                    'enabled': True, 'cert_path': 'server.der',
                    'key_path': 'server-key.der', 'client_ca_path': 'ca.der',
                }, self.api)
            reader = Reader()
            writer = Writer()
            await captured['handler'](reader, writer)
            self.assertTrue(reader.s.handshake_complete)
            self.assertIn(b'HTTP/1.1 200 OK', writer.payload)

        asyncio.run(exercise())

    def test_transport_failure_closes_socket_without_http_reply_and_logs_safe_context(self):
        for failure in (OSError(1), MemoryError('secret'), RuntimeError('secret')):
            with self.subTest(failure=type(failure).__name__):
                logs = []
                self.api.log_output = lambda *args: logs.append(args)

                class Reader:
                    async def read(stream_self, size):
                        raise failure
                    def get_extra_info(stream_self, name):
                        return ('192.0.2.1', 5)

                class Writer:
                    def __init__(stream_self):
                        stream_self.payload = bytearray()
                        stream_self.closed = False
                    def write(stream_self, data):
                        stream_self.payload.extend(data)
                    async def drain(stream_self):
                        pass
                    def close(stream_self):
                        stream_self.closed = True
                    async def wait_closed(stream_self):
                        pass

                async def exercise():
                    captured = {}
                    async def capture(handler, *args, **kwargs):
                        captured['handler'] = handler
                        return object()
                    with mock.patch.object(device_api, 'make_mtls_context', return_value=object()), \
                            mock.patch.object(device_api.tls_listener, 'start_server', side_effect=capture):
                        await device_api.start_device_api({
                            'enabled': True, 'cert_path': 'server.der',
                            'key_path': 'server-key.der', 'client_ca_path': 'ca.der',
                        }, self.api)
                    writer = Writer()
                    await captured['handler'](Reader(), writer)
                    self.assertTrue(writer.closed)
                    self.assertEqual(writer.payload, b'')
                    self.assertIn('stage=tls-handshake/request-headers', str(logs))
                    self.assertIn('peer=192.0.2.1', str(logs))
                    self.assertNotIn('secret', str(logs))
                asyncio.run(exercise())

    def test_server_reads_split_tls_post_without_header_read_ahead(self):
        events = []

        def reject_event(value, actor):
            events.append((value, actor))
            raise ValueError('controlled validation failure')

        api = DeviceAPI(
            self.broker, self.health, self.registry,
            lambda: {'device_name': 'test'},
            qualification_event=reject_event,
            operations=self.operations,
        )
        self.registry.enrol(
            self.cert, 'HIL rig', ('qualification:write',)
        )

        class TLSStream:
            def __init__(stream_self):
                stream_self.certificate_inspected = False

            def getpeercert(stream_self, binary_form=False):
                stream_self.certificate_inspected = True
                return self.cert

        class Reader:
            def __init__(stream_self):
                stream_self.s = TLSStream()
                stream_self.records = [
                    bytearray(
                        b'POST /api/v3/qualification/events HTTP/1.1\r\n'
                        b'Content-Type: application/json\r\n'
                        b'Content-Length: 2\r\n'
                        b'Idempotency-Key: 1.0123456789abcdef\r\n'
                        b'Connection: close\r\n\r\n'
                    ),
                    bytearray(b'{}'),
                ]
                stream_self.read_sizes = []

            async def read(stream_self, size):
                stream_self.read_sizes.append(size)
                while stream_self.records and not stream_self.records[0]:
                    stream_self.records.pop(0)
                if not stream_self.records:
                    return b''
                if stream_self.s.certificate_inspected:
                    raise OSError('TLS reads fail after certificate inspection')
                # Model the affected TLS stream: a read larger than the
                # current record does not return that record as a short read.
                if size > len(stream_self.records[0]):
                    return b''
                value = bytes(stream_self.records[0][:size])
                del stream_self.records[0][:size]
                return value

        class Writer:
            def __init__(stream_self):
                stream_self.payload = bytearray()

            def write(stream_self, payload):
                stream_self.payload.extend(payload)

            async def drain(stream_self):
                pass

            def close(stream_self):
                pass

            async def wait_closed(stream_self):
                pass

        async def exercise():
            captured = {}

            async def capture_server(handler, *_args, **_kwargs):
                captured['handler'] = handler
                return object()

            with mock.patch.object(device_api, 'make_mtls_context', return_value=object()), \
                    mock.patch.object(device_api.asyncio, 'start_server', side_effect=capture_server):
                await device_api.start_device_api({
                    'enabled': True, 'cert_path': 'server.der',
                    'key_path': 'server-key.der', 'client_ca_path': 'ca.der',
                }, api)
            reader = Reader()
            writer = Writer()
            await captured['handler'](reader, writer)
            self.assertIn(b'HTTP/1.1 400 Bad Request', writer.payload)
            self.assertIn(b'controlled validation failure', writer.payload)
            self.assertEqual(events[0][0], {})
            self.assertEqual(events[0][1], 'HIL rig')
            self.assertEqual(reader.read_sizes[-1], 2)
            self.assertNotIn(http_support.READ_BUFFER_BYTES, reader.read_sizes)

        asyncio.run(exercise())

    def test_v3_inventory_events_and_support_endpoints(self):
        self.registry.enrol(self.cert, 'dashboard', ('read',))
        self.health.record_event('boot_complete', component='startup')
        self.api.support_getter = lambda: {
            'format_version': 1, 'redaction': 'verified'
        }

        status, inventory = self.api.dispatch(
            'GET', '/api/v3/device/inventory', b'', self.cert
        )
        self.assertEqual(status, 200)
        self.assertEqual(inventory['api_version'], 3)
        self.assertEqual(inventory['modules'][0]['uuid'], '0001')

        status, events = self.api.dispatch(
            'GET', '/api/v3/events?cursor=0&limit=1', b'', self.cert
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(events['events']), 1)

        status, support = self.api.dispatch(
            'GET', '/api/v3/support', b'', self.cert
        )
        self.assertEqual(status, 200)
        self.assertEqual(support['redaction'], 'verified')

    def test_transport_neutral_contract_and_split_device_endpoints(self):
        self.registry.enrol(self.cert, 'dashboard', ('read',))
        self.api.device_getter = lambda: {
            'device_name': 'test', 'application_version': '2.5.0-beta.1',
            'board': 'esp32-s3', 'micropython_version': '1.29.0',
            'drivers': ['whes'], 'resources': [{'kind': 'uart', 'id': '1'}],
            'capabilities': {'features': {'usb_ncm': False}},
            'interfaces': {'wifi': {'state': 'online'}},
            'runtime': {'lifecycle': {'state': 'running'}},
            'boot': {'confirmed': True},
        }
        self.api.feature_flags = FeatureFlags()
        self.api.configuration_getter = lambda: {'release_channel': 'beta'}

        response = self.api.handle(APIRequest(
            'GET', '/api/v3/device', identity=self.cert, transport='usb-ncm'
        ))
        self.assertIsInstance(response, APIResponse)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.payload['device']['device_name'], 'test')
        self.assertNotIn('resources', response.payload['device'])

        expected = {
            '/api/v3/interfaces': 'interfaces',
            '/api/v3/hardware': 'hardware',
            '/api/v3/services': 'services',
            '/api/v3/configuration': 'configuration',
        }
        for path, key in expected.items():
            status, payload = self.api.dispatch('GET', path, b'', self.cert)
            self.assertEqual(status, 200)
            self.assertIn(key, payload)

    def test_restful_fleet_command_result_uses_path_identifier(self):
        class Fleet:
            def snapshot(fleet_self):
                return {'pending_commands': [{'id': 'command-7'}]}

            def complete_command(fleet_self, identifier, result, detail):
                self.assertEqual(identifier, 'command-7')
                return {'completed': identifier, 'result': result}

        registry_path = str(Path(self.temp.name) / 'fleet-clients.json')
        registry = api_security.ClientRegistry(registry_path)
        registry.enrol(self.cert, 'fleet', ('fleet:read', 'fleet:write'))
        api = DeviceAPI(
            self.broker, self.health, registry,
            lambda: {'device_name': 'test'}, fleet=Fleet()
        )
        status, result = api.dispatch(
            'POST', '/api/v3/fleet/commands/command-7/result',
            b'{"result":"complete"}', self.cert
        )
        self.assertEqual(status, 200)
        self.assertEqual(result['completed'], 'command-7')


if __name__ == '__main__':
    unittest.main()
