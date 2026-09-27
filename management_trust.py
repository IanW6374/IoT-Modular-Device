"""Application-owned Management Suite signing-key identity helpers.

This module deliberately has a distinct identity from ``update_security``.
Application releases can therefore add trust observability without requiring a
matching native-core generation to provide new helper functions.
"""

try:
    import uhashlib as hashlib
except ImportError:
    import hashlib

try:
    import ubinascii as binascii
except ImportError:
    import binascii


def normalized_key_bytes(value):
    value = bytes(value)
    if len(value) != 64:
        value = value.strip()
    if len(value) == 128:
        try:
            value = binascii.unhexlify(value)
        except Exception:
            return b''
    return value if len(value) == 64 else b''


def verification_key_fingerprint(path):
    try:
        with open(path, 'rb') as stream:
            value = normalized_key_bytes(stream.read())
        if not value:
            return ''
        return binascii.hexlify(hashlib.sha256(value).digest()).decode()
    except Exception:
        return ''


def verification_key_install_result(path):
    return {
        'message': 'Management Suite signing key installed and active. '
                   'SHA-256 fingerprint: ' + verification_key_fingerprint(path),
        'restart': False,
    }
