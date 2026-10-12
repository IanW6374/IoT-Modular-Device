"""Native routing and strict vectors; actual Mbed TLS C tests are opt-in."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
import update_security


def host_native(key, digest, signature):
    point = ec.EllipticCurvePublicNumbers(int.from_bytes(key[:32], 'big'),
        int.from_bytes(key[32:], 'big'), ec.SECP256R1()).public_key()
    try:
        point.verify(utils.encode_dss_signature(int.from_bytes(signature[:32], 'big'),
            int.from_bytes(signature[32:], 'big')), digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except InvalidSignature:
        return False


class NativeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.key = bytes(range(1, 33))
        public = update_security.public_key_bytes(self.key)
        self.point = (int.from_bytes(public[:32], 'big'), int.from_bytes(public[32:], 'big'))
        self.message = b'Native verifier contract'
        self.signature = update_security.sign_message(self.message, self.key)

    def test_native_path_never_runs_python_scalar_arithmetic(self):
        with mock.patch.object(update_security, '_native_p256_verify', side_effect=host_native) as native, \
             mock.patch.object(update_security, '_scalar_multiply', side_effect=AssertionError('Python ECC')):
            self.assertTrue(update_security.verify_message_signature(self.message, self.signature, self.point))
            self.assertFalse(update_security.verify_message_signature(b'tampered', self.signature, self.point))
        self.assertEqual(native.call_count, 2)

    def test_high_s_zero_scalars_bad_key_and_backend_truthy_results_fail_closed(self):
        raw = bytes.fromhex(self.signature)
        high = raw[:32] + (update_security._N - int.from_bytes(raw[32:], 'big')).to_bytes(32, 'big')
        with mock.patch.object(update_security, '_native_p256_verify', return_value=True) as native:
            for signature in (high.hex(), '0' * 128, raw[:32].hex() + '0' * 64):
                self.assertFalse(update_security.verify_message_signature(self.message, signature, self.point))
            self.assertFalse(update_security.verify_message_signature(self.message, self.signature,
                (self.point[0] + (1 << 256), self.point[1])))
            native.assert_not_called()
        with mock.patch.object(update_security, '_native_p256_verify', return_value=1):
            self.assertFalse(update_security.verify_message_signature(self.message, self.signature, self.point))

    def test_missing_native_binding_never_falls_back_on_device(self):
        with mock.patch.object(update_security, '_native_p256_verify', None), \
             mock.patch.object(update_security.sys, 'implementation', mock.Mock(name='implementation')) as implementation:
            implementation.name = 'micropython'
            with self.assertRaisesRegex(RuntimeError, 'Native P-256'):
                update_security.verify_message_signature(self.message, self.signature, self.point)


@unittest.skipUnless(os.environ.get('IOTMD_MBEDTLS_ROOT') and os.environ.get('IOTMD_MBEDCRYPTO_LIB'),
                     'Set pinned Mbed TLS source/library paths for actual C vectors')
class NativeCVectors(unittest.TestCase):
    def test_actual_native_helper_accepts_only_valid_canonical_signatures(self):
        root = Path(__file__).resolve().parents[1]
        source = r'''
#include <stdio.h>
#include <stdlib.h>
#include "iotmd_p256_verify.h"
static size_t decode(const char *text, unsigned char *out) {
    size_t size = strlen(text) / 2;
    if (size > 128 || strlen(text) % 2) { exit(2); }
    for(size_t i=0;i<size;i++) { unsigned byte; if(sscanf(text+i*2,"%2x",&byte)!=1)exit(2); out[i]=byte; }
    return size;
}
int main(int argc, char **argv) {
    if(argc!=4)return 2;
    unsigned char key[128], digest[128], signature[128];
    size_t k=decode(argv[1],key), d=decode(argv[2],digest), s=decode(argv[3],signature);
    puts(iotmd_p256_verify(key,k,digest,d,signature,s)?"valid":"invalid");
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'vectors.c').write_text(source)
            binary = path / 'vectors'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I',
                str(root / 'firmware/native'), '-I', str(Path(os.environ['IOTMD_MBEDTLS_ROOT']) / 'include'),
                str(path / 'vectors.c'), os.environ['IOTMD_MBEDCRYPTO_LIB'], '-o', str(binary)], check=True)
            def verify(key, digest, signature):
                return subprocess.check_output([str(binary), key.hex(), digest.hex(), signature.hex()], text=True).strip() == 'valid'
            for index in range(1, 17):
                private = ec.derive_private_key(index, ec.SECP256R1())
                point = private.public_key().public_numbers()
                key = point.x.to_bytes(32, 'big') + point.y.to_bytes(32, 'big')
                digest = hashlib.sha256(bytes([index])).digest()
                r, s = utils.decode_dss_signature(private.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256()))))
                s = min(s, update_security._N - s)
                signature = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
                self.assertTrue(verify(key, digest, signature))
                self.assertFalse(verify(key, hashlib.sha256(b'wrong').digest(), signature))
                self.assertFalse(verify(key, digest, signature[:32] + (update_security._N - s).to_bytes(32, 'big')))
                self.assertFalse(verify(key, digest, bytes(64)))
                self.assertFalse(verify(key, digest, update_security._N.to_bytes(32, 'big') + signature[32:]))
                self.assertFalse(verify(bytes(64), digest, signature))
                self.assertFalse(verify(key[:-1], digest, signature))
                self.assertFalse(verify(key, digest[:-1], signature))
                self.assertFalse(verify(key, digest, signature[:-1]))
