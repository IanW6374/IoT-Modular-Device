import hashlib
import tempfile
import unittest
from pathlib import Path

import management_trust
import update_security


class ManagementTrustTests(unittest.TestCase):
    def test_raw_and_hex_keys_have_one_normalized_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = update_security.public_key_bytes(bytes(range(1, 33)))
            raw_path = Path(directory) / 'raw.key'
            hex_path = Path(directory) / 'hex.key'
            raw_path.write_bytes(raw)
            hex_path.write_text(raw.hex() + '\n')
            expected = hashlib.sha256(raw).hexdigest()

            self.assertEqual(
                management_trust.verification_key_fingerprint(raw_path), expected
            )
            self.assertEqual(
                management_trust.verification_key_fingerprint(hex_path), expected
            )
            self.assertIn(
                expected,
                management_trust.verification_key_install_result(raw_path)['message'],
            )

    def test_invalid_or_missing_key_has_no_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'key'
            self.assertEqual(
                management_trust.verification_key_fingerprint(path), ''
            )
            path.write_bytes(b'invalid')
            self.assertEqual(
                management_trust.verification_key_fingerprint(path), ''
            )
