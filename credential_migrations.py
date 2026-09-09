"""Pure, non-mutating encrypted-configuration schema migrations."""

try:
    import ujson as json
except ImportError:
    import json

from credential_schema import DEFAULT_PORTAL_MAX_RETRIES, SCHEMA_VERSION


def migrate(config):
    value = json.loads(json.dumps(config))
    if int(value.get('schema', 0)) == 4:
        value['schema'] = 5
        value['api'] = {
            'enabled': False,
            'port': getattr(__import__('device_config'), 'DEVICE_API_PORT', 8444),
            'auth': 'mtls',
        }
    if int(value.get('schema', 0)) == 5:
        value['schema'] = 7
        portal = value.setdefault('portal', {})
        if int(portal.get('session_timeout_s', 28800)) == 28800:
            portal['session_timeout_s'] = 3600
    if int(value.get('schema', 0)) == 6:
        value['schema'] = 7
        portal = value.setdefault('portal', {})
        portal['users'] = [{
            'username': portal.get('username', 'admin'),
            'password_verifier': portal.get('password_verifier', ''),
            'role': 'administrator', 'enabled': True,
        }]
    if int(value.get('schema', 0)) == 7:
        value['schema'] = SCHEMA_VERSION
        portal = value.setdefault('portal', {})
        timeout = int(portal.get('session_timeout_s', 3600) or 3600)
        for user in portal.get('users', ()):
            user.update({
                'max_retries': DEFAULT_PORTAL_MAX_RETRIES,
                'failed_attempts': 0, 'locked': False,
                'session_timeout_s': timeout,
                'password_change_required': False,
            })
    return value
