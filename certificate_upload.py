"""Stage certificate and trust payloads received by portal or device API."""

import api_security
import certificate_manager
import fleet_management


def _paths(runtime_paths):
    paths = dict(runtime_paths)
    paths.update({
        'management-suite-key': fleet_management.FLEET_VERIFICATION_KEY_PATH,
        'api-client-ca': 'certs/api-client-ca-stage.der',
        'api-client-cert': 'certs/api-client-enrol.der',
        'fleet-client-cert': 'certs/fleet-client-enrol.der',
        'qualification-client-cert': 'certs/qualification-client-enrol.der',
        'iot-ca-enrollment': 'certs/.iot-ca-enrollment.manual',
    })
    return paths


def stage(kind, payload, runtime_paths, client_scopes=''):
    path = _paths(runtime_paths).get(kind)
    if not path:
        raise ValueError('unknown certificate type')
    payload = bytes(payload)
    if not payload or len(payload) > 16384:
        raise ValueError('certificate file size is invalid')
    if b'-----BEGIN' in payload and kind != 'portal-cert':
        raise ValueError('only the portal certificate chain may use PEM')
    client_kinds = (
        'api-client-ca', 'api-client-cert', 'fleet-client-cert',
        'qualification-client-cert',
    )
    if kind in client_kinds:
        certificate_manager.decode_certificate(payload)
        fingerprint = api_security.certificate_fingerprint(payload)[:24]
        prefixes = {
            'api-client-ca': 'certs/.api-ca-stage-',
            'api-client-cert': 'certs/.api-client-stage-',
            'fleet-client-cert': 'certs/.fleet-client-stage-',
            'qualification-client-cert': 'certs/.qualification-client-stage-',
        }
        path = prefixes[kind] + fingerprint + '.der'
    scopes = (
        api_security.normalize_client_scopes(
            client_scopes or api_security.CLIENT_SCOPE_PRESETS[kind]
        ) if kind in api_security.CLIENT_SCOPE_PRESETS else ''
    )
    with open(path + '.manual', 'wb') as stream:
        stream.write(payload)
    if kind in client_kinds[1:]:
        api_security.stage_client_scopes(path, kind, scopes)
    return {'kind': kind, 'size': len(payload), 'staged': True}


async def read_and_stage(kind, reader, length, runtime_paths, client_scopes=''):
    payload = bytearray()
    while len(payload) < length:
        chunk = await reader.read(min(1024, length - len(payload)))
        if not chunk:
            raise ValueError('certificate upload ended early')
        payload.extend(chunk)
    return stage(kind, payload, runtime_paths, client_scopes)
