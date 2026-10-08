"""Versioned HTTPS device API with mandatory mutual TLS authentication."""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import ujson as json
except ImportError:
    import json

try:
    import ussl as ssl
except ImportError:
    import ssl

import http_support
import tls_listener
from api_security import APIAuthorizationError
from api_contracts import APIRequest, APIResponse
from api_operations import OperationError, MAX_OPERATIONS, MAX_CLIENTS, MAX_RESULT_BYTES, MAX_RESULT_STORAGE
from portal_http import is_client_disconnect_error, is_http_timeout_error


API_VERSION = 3
API_KEEP_ALIVE_REQUESTS = 32
API_KEEP_ALIVE_TIMEOUT_SECONDS = 30
CONFIGURATION_BACKUP_BODY_BYTES = 384 * 1024


def error_payload(status, message):
    """Stable v3 errors; no automatic mutation retry is safe on this device."""
    return {'api_version': API_VERSION, 'error': {
        'code': {400: 'invalid_request', 403: 'permission_denied',
                 404: 'not_found', 405: 'method_not_allowed',
                 410: 'unsupported_api_version', 413: 'body_too_large',
                 503: 'service_unavailable'}.get(status, 'request_failed'),
        'message': str(message)[:256], 'retryable': False,
    }}


def request_body_limit(path, configured_maximum):
    """Return the bounded body limit for one API route.

    Complete encrypted backup envelopes can contain the maximum 128 KiB
    plaintext backup as hex-encoded authenticated ciphertext. Keep that
    exceptional allowance local to restore preview; ordinary commands retain
    the device's configured (and usually much smaller) request limit.
    """
    route = str(path).split('?', 1)[0]
    configured_maximum = int(configured_maximum)
    if route == '/api/v3/configuration/backups/preview':
        return max(configured_maximum, CONFIGURATION_BACKUP_BODY_BYTES)
    return configured_maximum


def make_mtls_context(cert_path, key_path, client_ca_path):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    ca_paths = (
        list(client_ca_path)
        if isinstance(client_ca_path, (list, tuple)) else [client_ca_path]
    )
    ca_paths = [path for path in ca_paths if path]
    if not ca_paths:
        raise RuntimeError('at least one API client CA is required')
    for path in ca_paths:
        try:
            context.load_verify_locations(cafile=path)
        except TypeError:
            with open(path, 'rb') as stream:
                context.load_verify_locations(cadata=stream.read())
    if not hasattr(ssl, 'CERT_REQUIRED'):
        raise RuntimeError('this TLS runtime cannot require client certificates')
    context.verify_mode = ssl.CERT_REQUIRED
    return context


class DeviceAPI:
    def __init__(self, broker, health, registry, device_getter, log_output=None,
                 fleet=None, support_getter=None, feature_flags=None,
                 configuration_getter=None, qualification_getter=None,
                 configuration_profile_applier=None, qualification_event=None,
                 qualification_scenario=None, certificate_stager=None,
                 certificate_applier=None, network_confirmer=None,
                 configuration_restarter=None, configuration_backup=None,
                 configuration_restore_preview=None,
                 configuration_restore_apply=None, operations=None):
        self.broker = broker
        self.health = health
        self.registry = registry
        self.device_getter = device_getter
        self.log_output = log_output
        self.fleet = fleet
        self.support_getter = support_getter
        self.feature_flags = feature_flags
        self.configuration_getter = configuration_getter
        self.configuration_profile_applier = configuration_profile_applier
        self.qualification_getter = qualification_getter
        self.qualification_event = qualification_event
        self.qualification_scenario = qualification_scenario
        self.certificate_stager = certificate_stager
        self.certificate_applier = certificate_applier
        self.network_confirmer = network_confirmer
        self.configuration_restarter = configuration_restarter
        self.configuration_backup = configuration_backup
        self.configuration_restore_preview = configuration_restore_preview
        self.configuration_restore_apply = configuration_restore_apply
        self.operations = operations
        self._operation_id = ''
        if operations and hasattr(broker, 'add_listener'):
            previous = getattr(operations, '_broker_listener', None)
            if previous and hasattr(broker, 'remove_listener'):
                broker.remove_listener(previous)
            broker.add_listener(self._operation_completed)
            operations._broker_listener = self._operation_completed

    def _operation_completed(self, value):
        if value.get('status') not in ('complete', 'failed') or value.get('source') != 'api':
            return
        for record in self.operations.state['records']:
            if (record['id'] == value['id'] and value.get('identity') == record['client'][:16]
                    and record['state'] not in ('complete', 'failed', 'interrupted')):
                try:
                    self.operations.finish(record, 200, value, value['status'])
                except (RuntimeError, OSError):
                    self.operations.update(record['id'], record['client'], state='interrupted')
                return

    def connection_opened(self, identity, peer='unknown'):
        client = self.registry.identify(identity)
        if self.log_output:
            self.log_output(
                'API', 'Connection',
                {'log': (
                    'Accepted ' + str(client.get('label', 'client')) +
                    ' from ' + str(peer)
                ), 'force': True, 'audit': True},
                'INFO'
            )
        return client

    def dispatch(self, method, path, body, identity, authenticated_client=None):
        """Internal tuple adapter; exceptions are handled by the transport."""
        return self._dispatch(method, path, body, identity, authenticated_client)

    def handle(self, request):
        """Handle an APIRequest without depending on its concrete transport."""
        record = None
        try:
            route, client = self._authenticate(request.method, request.path,
                request.identity, request.client)
            if request.method == 'POST' and route.startswith('/api/v3/'):
                if self.operations is None:
                    raise OperationError('durable_operations_unavailable',
                        'Durable operation storage is unavailable; writes are disabled', 503)
                body = request.body.encode() if isinstance(request.body, str) else bytes(request.body)
                record, replay = self.operations.reserve(client['fingerprint'],
                    request.headers.get('idempotency-key'), request.method,
                    request.path, body)
                if replay:
                    status, payload = self.operations.result(record['id'], record['client'])
                    payload['api_version'] = API_VERSION
                    return APIResponse(status, payload)
                self._operation_id = record['id']
            status, payload = self._dispatch(
                request.method, request.path, request.body, request.identity,
                request.client
            )
        except OperationError as exc:
            self._record_failure(request, exc)
            status, payload = exc.status, error_payload(exc.status, exc)
            payload['error'].update(code=exc.code, operation_id=exc.operation_id)
            record = None
        except APIAuthorizationError as exc:
            self._record_failure(request, exc)
            status, payload = 403, error_payload(403, exc)
        except KeyError as exc:
            self._record_failure(request, exc)
            status, payload = 404, error_payload(404, exc)
        except ValueError as exc:
            self._record_failure(request, exc)
            status, payload = 400, error_payload(400, exc)
        except RuntimeError as exc:
            self._record_failure(request, exc)
            status, payload = 503, error_payload(503, exc)
        except OSError as exc:
            self._record_failure(request, exc)
            status, payload = 503, error_payload(503, 'Storage or device I/O failed; reconcile before another write')
        finally:
            self._operation_id = ''
        if status >= 400 and isinstance(payload.get('error'), str):
            payload = error_payload(status, payload['error'])
        else:
            payload = dict(payload)
            payload['api_version'] = API_VERSION
        if record:
            state = 'failed' if status >= 400 else 'complete'
            if status == 503:
                state = 'interrupted'
            elif status < 400 and request.path.split('?', 1)[0].endswith('/commands'):
                state = 'queued'
            try:
                payload['operation'] = self.operations.finish(record, status, payload, state)
            except (RuntimeError, OSError):
                try:
                    self.operations.update(record['id'], record['client'], state='interrupted')
                except (RuntimeError, OSError):
                    pass  # Reservation remains: fail closed rather than repeating I/O.
                payload = error_payload(503, 'Outcome could not be recorded; do not repeat the mutation')
                payload['error'].update(code='operation_outcome_uncertain', operation_id=record['id'])
                status = 503
        return APIResponse(status, payload)

    def _record_failure(self, request, error):
        if self.health:
            self.health.increment('api_failures')
        if self.log_output:
            self.log_output('API', 'Request rejected', {
                'log': request.method + ' ' + request.path.split('?', 1)[0] +
                       ': ' + str(error)[:256],
                'force': True, 'audit': True,
            }, 'ERROR')

    def _authenticate(self, method, path, identity, authenticated_client=None):
        route = str(path).split('?', 1)[0]
        is_fleet = route.startswith('/api/v3/fleet')
        is_qualification = route.startswith('/api/v3/qualification')
        if route.startswith('/api/v3/configuration/') and method == 'POST':
            scope = 'configuration:write'
        elif is_qualification and method == 'POST':
            scope = (
                'qualification:execute'
                if route.startswith('/api/v3/qualification/scenarios/')
                else 'qualification:write'
            )
        elif is_fleet:
            scope = 'fleet:write' if method == 'POST' else 'fleet:read'
        else:
            scope = 'write' if method == 'POST' else 'read'
        if authenticated_client is None:
            client = self.registry.authenticate(identity, scope)
        else:
            # Recheck the cached fingerprint against the live registry so
            # revocation remains immediate without rehashing the DER
            # certificate on every request in this TLS connection.
            client = self.registry.authenticate_fingerprint(
                authenticated_client.get('fingerprint', ''), scope
            )
        return route, client

    def _dispatch(self, method, path, body, identity, authenticated_client=None):
        route, client = self._authenticate(method, path, identity, authenticated_client)
        self._record_request(client, method, route)

        if route == '/api/v2' or route.startswith('/api/v2/'):
            return 410, {'error': 'Device API v2 is retired; use /api/v3'}
        if method == 'GET' and route == '/api/v3':
            return 200, {
                'api_version': API_VERSION,
                'capabilities': {
                    'configuration_profiles': bool(self.configuration_profile_applier),
                    'encrypted_backups': bool(self.configuration_backup),
                    'restore_preview': bool(self.configuration_restore_preview),
                    'restore_apply': bool(self.configuration_restore_apply),
                    'certificates': bool(self.certificate_stager and self.certificate_applier),
                    'fleet': bool(self.fleet),
                    'qualification': bool(self.qualification_getter),
                    'module_operations': True,
                    'persistent_idempotency': bool(self.operations),
                },
                'next_request_sequence': self.operations.next_sequence(client['fingerprint']) if self.operations else None,
                'limits': {
                    'retained_operations': MAX_OPERATIONS,
                    'operation_clients': MAX_CLIENTS,
                    'operation_result_bytes': MAX_RESULT_BYTES,
                    'operation_result_storage_bytes': MAX_RESULT_STORAGE,
                    'request_body_bytes': getattr(self, 'maximum_body_bytes', 8192),
                    'restore_preview_body_bytes': request_body_limit(
                        '/api/v3/configuration/backups/preview',
                        getattr(self, 'maximum_body_bytes', 8192)),
                    'keep_alive_requests': API_KEEP_ALIVE_REQUESTS,
                    'keep_alive_timeout_seconds': API_KEEP_ALIVE_TIMEOUT_SECONDS,
                },
            }

        if method == 'GET' and route == '/api/v3/device':
            return 200, {
                'api_version': API_VERSION,
                'device': self._device_section('device'),
            }
        if method == 'GET' and route == '/api/v3/interfaces':
            return 200, {
                'api_version': API_VERSION,
                'interfaces': self._device_section('interfaces'),
            }
        if method == 'GET' and route == '/api/v3/hardware':
            return 200, {
                'api_version': API_VERSION,
                'hardware': self._device_section('hardware'),
            }
        if method == 'GET' and route == '/api/v3/services':
            return 200, {
                'api_version': API_VERSION,
                'services': self._device_section('services'),
            }
        if method == 'GET' and route == '/api/v3/configuration':
            value = self.configuration_getter() if self.configuration_getter else {}
            return 200, {'api_version': API_VERSION, 'configuration': value}
        if method == 'POST' and route == '/api/v3/configuration/profile':
            if not self.configuration_profile_applier:
                raise RuntimeError('configuration profile management is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            if not isinstance(value, dict):
                raise ValueError('configuration profile must be an object')
            result = self.configuration_profile_applier(
                value, str(client.get('label', 'API client'))
            )
            return 202, {'accepted': True, 'profile': result}
        if method == 'POST' and route == '/api/v3/configuration/backups':
            if not self.configuration_backup:
                raise RuntimeError('complete configuration backup is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            if not isinstance(value, dict):
                raise ValueError('configuration backup request must be an object')
            if not value.get('derived_key'):
                raise ValueError(
                    'managed backup requires IoT-MD Management 2.7.3 or newer'
                )
            return 201, {
                'backup': self.configuration_backup(value)
            }
        if method == 'POST' and route == '/api/v3/configuration/backups/preview':
            if not self.configuration_restore_preview:
                raise RuntimeError('complete configuration restore is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            if not isinstance(value, dict):
                raise ValueError('configuration restore request must be an object')
            if not value.get('derived_key'):
                raise ValueError(
                    'managed backup preview requires IoT-MD Management 2.7.3 or newer'
                )
            return 200, {'preview': self.configuration_restore_preview(value)}
        if method == 'POST' and route == '/api/v3/configuration/backups/apply':
            if not self.configuration_restore_apply:
                raise RuntimeError('complete configuration restore is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            if not isinstance(value, dict):
                raise ValueError('configuration restore request must be an object')
            return 202, {
                'accepted': True,
                'restore': self.configuration_restore_apply(value.get('token', '')),
            }
        certificate_prefix = '/api/v3/configuration/certificates/'
        if method == 'POST' and route == certificate_prefix + 'apply':
            if not self.certificate_applier:
                raise RuntimeError('certificate profile management is unavailable')
            return 202, {
                'accepted': True, 'certificates': self.certificate_applier()
            }
        if method == 'POST' and route.startswith(certificate_prefix):
            if not self.certificate_stager:
                raise RuntimeError('certificate profile management is unavailable')
            kind = route[len(certificate_prefix):]
            if not kind or '/' in kind:
                raise ValueError('certificate type is invalid')
            return 202, {
                'accepted': True,
                'certificate': self.certificate_stager(kind, body),
            }
        if method == 'POST' and route == '/api/v3/configuration/network/confirm':
            if not self.network_confirmer:
                raise RuntimeError('network confirmation is unavailable')
            return 200, {
                'confirmed': bool(self.network_confirmer())
            }
        if method == 'POST' and route == '/api/v3/configuration/restart':
            if not self.configuration_restarter:
                raise RuntimeError('configuration restart is unavailable')
            return 202, {
                'accepted': True, 'restart': self.configuration_restarter()
            }
        if method == 'GET' and route == '/api/v3/qualification':
            if not self.qualification_getter:
                raise RuntimeError('qualification recorder is unavailable')
            return 200, {
                'api_version': API_VERSION,
                'qualification': self.qualification_getter(),
            }
        if method == 'POST' and route == '/api/v3/qualification/events':
            if not self.qualification_event:
                raise RuntimeError('qualification evidence recording is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            result = self.qualification_event(
                value, str(client.get('label', 'API client'))
            )
            return 202, {'accepted': True, 'event': result}
        scenario_prefix = '/api/v3/qualification/scenarios/'
        if method == 'POST' and route.startswith(scenario_prefix):
            if not self.qualification_scenario:
                raise RuntimeError('qualification scenario execution is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            if not isinstance(value, dict):
                raise ValueError('qualification scenario must be an object')
            value = dict(value)
            value['scenario'] = route[len(scenario_prefix):]
            result = self.qualification_scenario(
                value, str(client.get('label', 'API client'))
            )
            return 202, {'accepted': True, 'scenario': result}

        if method == 'GET' and route == '/api/v3/device/inventory':
            return 200, {
                'api_version': API_VERSION,
                'device': self.device_getter(),
                'modules': self.broker.catalog(),
                'fleet': self.fleet.snapshot() if self.fleet else None,
            }
        if method == 'GET' and route == '/api/v3/health':
            return 200, {
                'api_version': API_VERSION, 'health': self.health.snapshot()
            }
        if method == 'GET' and route == '/api/v3/events':
            cursor = self._query_integer(path, 'cursor', 0)
            limit = self._query_integer(path, 'limit', 32)
            return 200, self.health.events_since(cursor, limit)
        if method == 'GET' and route == '/api/v3/support':
            if not self.support_getter:
                raise RuntimeError('support bundle is unavailable')
            return 200, self.support_getter()
        if method == 'GET' and route == '/api/v3/fleet':
            if not self.fleet:
                raise RuntimeError('fleet management is unavailable')
            return 200, self.fleet.snapshot()
        if method == 'POST' and route == '/api/v3/fleet/policy':
            if not self.fleet:
                raise RuntimeError('fleet management is unavailable')
            policy = json.loads(body.decode() if isinstance(body, bytes) else body)
            result = self.fleet.apply_policy(policy)
            self.health.record_event(
                'fleet_policy_applied', 'Applied fleet policy',
                {'policy_sequence': result['policy_sequence']}, force=True,
                component='fleet'
            )
            return 202, result
        if method == 'POST' and (
            route == '/api/v3/fleet/command-result' or
            (
                route.startswith('/api/v3/fleet/commands/') and
                route.endswith('/result')
            )
        ):
            if not self.fleet:
                raise RuntimeError('fleet management is unavailable')
            value = json.loads(body.decode() if isinstance(body, bytes) else body)
            if not isinstance(value, dict):
                raise ValueError('command result must be an object')
            route_identifier = (
                route.split('/')[-2]
                if route.startswith('/api/v3/fleet/commands/') else ''
            )
            result = self.fleet.complete_command(
                route_identifier or value.get('id', ''), value.get('result', 'complete'),
                value.get('detail', '')
            )
            return 200, result

        if method == 'GET' and route == '/api/v3/modules':
            return 200, {'api_version': API_VERSION, 'modules': self.broker.catalog()}
        if method == 'GET' and (route == '/api/v3/operations' or route.startswith('/api/v3/operations/')) and not self.operations:
            raise RuntimeError('Durable operation storage is unavailable')
        if method == 'GET' and route == '/api/v3/operations' and self.operations:
            return 200, {'operations': [self.operations.public(item) for item in self.operations.state['records']
                if item['client'] == client['fingerprint']]}
        if method == 'GET' and route.startswith('/api/v3/operations/') and self.operations:
            parts = route[len('/api/v3/operations/'):].split('/')
            if len(parts) == 2 and parts[1] == 'result':
                return self.operations.result(parts[0], client['fingerprint'])
            if len(parts) == 1:
                return 200, self.operations.operation(parts[0], client['fingerprint'])
            return 404, {'error': 'operation endpoint not found'}
        prefix = '/api/v3/modules/'
        if route.startswith(prefix):
            remainder = route[len(prefix):]
            parts = remainder.split('/')
            if len(parts) == 2:
                uuid, action = parts
                if method == 'GET' and action == 'state':
                    try:
                        state = self.broker.state(uuid)
                    except KeyError:
                        return self._module_not_found(client, uuid)
                    return 200, {'module': uuid, 'state': state}
                if method == 'GET' and action == 'diagnostics':
                    try:
                        diagnostics = self.broker.diagnostics(uuid)
                    except KeyError:
                        return self._module_not_found(client, uuid)
                    return 200, {'module': uuid, 'diagnostics': diagnostics}
                if method == 'POST' and action == 'commands':
                    command = json.loads(body.decode() if isinstance(body, bytes) else body)
                    if self._operation_id and isinstance(command, dict):
                        command['request_id'] = self._operation_id
                    try:
                        operation = self.broker.submit(
                            uuid, command, 'api', client.get('fingerprint', '')[:16]
                        )
                    except KeyError:
                        return self._module_not_found(client, uuid)
                    if self.health:
                        self.health.increment('api_commands')
                    self._audit(client, uuid, operation['id'])
                    return 202, operation
        return 404, {'error': 'endpoint not found'}

    def _device_section(self, section):
        value = self.device_getter()
        if not isinstance(value, dict):
            return {}
        if section == 'device':
            excluded = {
                'drivers', 'resources', 'runtime', 'boot', 'capabilities',
                'interfaces', 'features',
            }
            return {key: value[key] for key in value if key not in excluded}
        if section == 'interfaces':
            return dict(value.get('interfaces', {}))
        if section == 'hardware':
            return {
                'board': value.get('board', ''),
                'micropython_version': value.get('micropython_version', ''),
                'drivers': value.get('drivers', []),
                'resources': value.get('resources', []),
                'capabilities': value.get('capabilities', {}),
            }
        if section == 'services':
            result = {
                'runtime': value.get('runtime', {}),
                'boot': value.get('boot', {}),
            }
            if self.feature_flags is not None:
                result['feature_flags'] = self.feature_flags.snapshot()
            return result
        return {}

    @staticmethod
    def _query_integer(path, name, default):
        query = str(path).split('?', 1)
        if len(query) == 1:
            return default
        for item in query[1].split('&'):
            key_value = item.split('=', 1)
            if key_value[0] == name:
                return int(key_value[1]) if len(key_value) == 2 else default
        return default

    def _record_request(self, client, method, route):
        label = str(client.get('label', 'client'))
        if self.health:
            count = self.health.increment('api_requests')
            # Keep routine reads as an aggregate counter so polling clients do
            # not displace significant history or cause excessive flash wear.
            if method == 'POST' or count % 100 == 0:
                self.health.record_event(
                    'api_request', str(method) + ' ' + str(route),
                    {'client': label, 'request_count': count}, force=False,
                    component='api'
                )
        if self.log_output:
            self.log_output(
                'API', 'Request',
                {'log': label + ' ' + str(method) + ' ' + str(route)}, 'DEBUG'
            )

    def _module_not_found(self, client, uuid):
        if self.health:
            self.health.increment('api_failures')
            self.health.record_event(
                'api_not_found', 'Unknown module UUID ' + str(uuid),
                {'client': str(client.get('label', 'client'))}, force=False,
                severity='warning', component='api'
            )
        return 404, {'error': 'module not found', 'module': uuid}

    def _audit(self, client, uuid, operation_id):
        if self.log_output:
            self.log_output(
                'API', 'Module command',
                {'log': (
                    str(client.get('label', 'client')) + ' requested module ' +
                    str(uuid) + ' operation ' + str(operation_id)
                ), 'force': True, 'audit': True},
                'INFO'
            )


async def _write_response(writer, status, payload, keep_alive=False):
    if status >= 400 and isinstance(payload.get('error'), str):
        payload = error_payload(status, payload['error'])
    reason = {
        200: 'OK', 201: 'Created', 202: 'Accepted', 400: 'Bad Request',
        401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
        405: 'Method Not Allowed', 409: 'Conflict', 410: 'Gone', 413: 'Payload Too Large',
        503: 'Service Unavailable',
    }.get(status, 'Error')
    body = json.dumps(payload).encode()
    headers = http_support.add_security_headers((
        ('Cache-Control', 'no-store'),
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Content-Length', str(len(body))),
        ('Connection', 'keep-alive' if keep_alive else 'close'),
    ))
    writer.write(
        ('HTTP/1.1 ' + str(status) + ' ' + reason + '\r\n' +
         ''.join(name + ': ' + value + '\r\n' for name, value in headers) +
         '\r\n').encode() + body
    )
    await writer.drain()


def _peer_certificate(reader):
    stream = getattr(reader, 's', None)
    if stream is None or not hasattr(stream, 'getpeercert'):
        raise APIAuthorizationError('TLS peer certificate is unavailable')
    value = stream.getpeercert(True)
    if not value:
        raise APIAuthorizationError('client certificate is required')
    return value


def _peer_address(reader, writer=None):
    for stream in (reader, writer):
        getter = getattr(stream, 'get_extra_info', None)
        if getter:
            try:
                value = getter('peername')
                if value:
                    return str(value[0] if isinstance(value, tuple) else value)
            except Exception:
                pass
        socket_value = getattr(stream, 's', None)
        if socket_value is not None and hasattr(socket_value, 'getpeername'):
            try:
                value = socket_value.getpeername()
                return str(value[0] if isinstance(value, tuple) else value)
            except Exception:
                pass
    return 'unknown'


async def _start_http_device_api(settings, api):
    if not settings.get('enabled'):
        return None
    maximum = int(settings.get('max_body_bytes', 8192))
    api.maximum_body_bytes = maximum

    async def handle(reader, writer):
        peer = _peer_address(reader, writer)
        stage = 'tls-handshake/request-headers'
        http_ready = False
        try:
            # MicroPython's TLS server defers the handshake until the first
            # stream read. Inspecting the certificate before that read resets
            # otherwise valid clients during ClientHello.
            identity = None
            authenticated_client = None
            for request_number in range(API_KEEP_ALIVE_REQUESTS):
                stage = ('tls-handshake/request-headers' if identity is None
                         else 'request-headers')
                line, headers = await http_support.read_request(
                    reader, API_KEEP_ALIVE_TIMEOUT_SECONDS
                )
                if not line:
                    return
                http_ready = True
                parts = line.decode().strip().split()
                if len(parts) != 3:
                    raise ValueError('invalid HTTP request line')
                method, path, version = parts
                if method not in ('GET', 'POST'):
                    await _write_response(writer, 405, {'error': 'method not allowed'})
                    return
                length = int(headers.get('content-length', '0') or 0)
                stage = 'request-body'
                body_maximum = request_body_limit(path, maximum)
                body = await http_support.read_exact_body(
                    reader, length, body_maximum
                ) if length else b''
                if identity is None:
                    # On the MicroPython TLS stream, inspecting the peer
                    # certificate between header and body reads can disturb
                    # subsequent application-data reads. The SSL context has
                    # already required and verified a client certificate, so
                    # receive the bounded body before extracting its identity.
                    stage = 'peer-certificate'
                    identity = _peer_certificate(reader)
                    authenticated_client = api.connection_opened(identity, peer)
                stage = 'dispatch'
                response = api.handle(APIRequest(
                    method, path, body, identity, authenticated_client,
                    transport='https', peer=peer, headers=headers
                ))
                status, payload = response.as_tuple()
                connection = str(headers.get('connection', '')).lower()
                keep_alive = (
                    request_number < API_KEEP_ALIVE_REQUESTS - 1 and
                    connection != 'close' and
                    (version == 'HTTP/1.1' or connection == 'keep-alive')
                )
                stage = 'response-write'
                await _write_response(writer, status, payload, keep_alive)
                if not keep_alive:
                    return
        except APIAuthorizationError as exc:
            if api.health:
                api.health.increment('api_failures')
            if api.log_output:
                api.log_output(
                    'API', 'Connection',
                    {'log': 'Rejected from ' + peer + ': ' + str(exc),
                     'force': True, 'audit': True},
                    'ERROR'
                )
            await _write_response(writer, 403, {'error': str(exc)})
        except KeyError as exc:
            await _write_response(writer, 404, {'error': str(exc)})
        except RuntimeError as exc:
            if api.health:
                api.health.increment('api_failures')
            tls_listener.report_failure(api.log_output, 'API', stage, exc, peer)
            if http_ready:
                await _write_response(writer, 503, {'error': str(exc)})
        except Exception as exc:
            if is_http_timeout_error(exc) or is_client_disconnect_error(exc):
                if is_http_timeout_error(exc) and not http_ready:
                    tls_listener.report_failure(api.log_output, 'API', stage, exc, peer)
                return
            if api.health:
                api.health.increment('api_failures')
            tls_listener.report_failure(api.log_output, 'API', stage, exc, peer)
            # No HTTP reply on an unestablished or failed TLS transport.
            if http_ready and not isinstance(exc, (OSError, MemoryError)):
                await _write_response(writer, 400, {'error': str(exc)})
        finally:
            await http_support.close_writer(writer)

    context = make_mtls_context(
        settings['cert_path'], settings['key_path'], settings['client_ca_paths']
        if 'client_ca_paths' in settings else settings['client_ca_path']
    )
    return await tls_listener.start_server(
        handle, settings.get('host', '0.0.0.0'), int(settings.get('port', 8444)),
        backlog=2, ssl=context, log_output=api.log_output, service='API'
    )


class DeviceAPIHTTPTransport:
    """HTTPS/mTLS adapter for the transport-neutral DeviceAPI contract."""

    def __init__(self, settings, api):
        self.settings = settings
        self.api = api
        self.server = None

    async def start(self):
        self.server = await _start_http_device_api(self.settings, self.api)
        return self.server

    async def stop(self):
        if self.server is not None and hasattr(self.server, 'close'):
            self.server.close()
            waiter = getattr(self.server, 'wait_closed', None)
            if waiter:
                await waiter()
        self.server = None


async def start_device_api(settings, api):
    """Compatibility entry point returning the concrete listener object."""
    return await DeviceAPIHTTPTransport(settings, api).start()
