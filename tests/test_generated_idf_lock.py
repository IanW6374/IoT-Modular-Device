import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.build_micropython_firmware import generated_idf_lock_only


class GeneratedIDFLockTests(unittest.TestCase):
    def test_only_exact_generated_patch_version_change_is_allowed(self):
        relative = 'ports/esp32/lockfiles/dependencies.lock.esp32s3'
        original = 'dependencies:\n  idf:\n    version: 5.5.2\n'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / relative
            target.parent.mkdir(parents=True)
            target.write_text(original.replace('5.5.2', '5.5.5'))
            with patch('tools.build_micropython_firmware.run', return_value=SimpleNamespace(stdout=original)):
                self.assertTrue(generated_idf_lock_only(directory, ' M ' + relative, 'v5.5.5'))
                self.assertFalse(generated_idf_lock_only(directory, ' M source.c', 'v5.5.5'))
                self.assertFalse(generated_idf_lock_only(directory, ' M ' + relative + '\n M source.c', 'v5.5.5'))
                target.write_text(original.replace('5.5.2', '5.5.4'))
                self.assertFalse(generated_idf_lock_only(directory, ' M ' + relative, 'v5.5.5'))
                target.write_text(original.replace('5.5.2', '5.5.5') + 'extra: change\n')
                self.assertFalse(generated_idf_lock_only(directory, ' M ' + relative, 'v5.5.5'))
