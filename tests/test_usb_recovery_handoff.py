import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import recovery_boot


class USBRecoveryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.directory.name)
        self.bundle = b'signed application test fixture'
        Path('.app-update.bundle').write_bytes(self.bundle)
        self.marker = {'format_version': 1, 'core_version': 'alpha97',
                       'partition': 'ota_1', 'application_size': len(self.bundle),
                       'application_sha256': hashlib.sha256(self.bundle).hexdigest()}
        self.app = SimpleNamespace(BUNDLE_PATH='.app-update.bundle',
            stage_bundle=Mock(return_value={'has_application': True,
                'selected_paths': ['iotmd.py', 'app_settings.json'], 'version': 'alpha97'}),
            discard_pending_update=Mock())
        self.partition = Mock(return_value=SimpleNamespace(info=lambda: (0, 0, 0, 0, 'ota_1')))
        self.partition.RUNNING = 0
        self.partition.mark_app_valid_cancel_rollback = Mock()
        self.modules = {'app_update': self.app,
            'credential_store': SimpleNamespace(is_provisioned=lambda: False),
            'core_metadata': SimpleNamespace(CORE_FIRMWARE_VERSION='alpha97'),
            'machine': SimpleNamespace(WDT=lambda identifier: SimpleNamespace(feed=lambda: None)),
            'esp32': SimpleNamespace(Partition=self.partition)}

    def tearDown(self):
        os.chdir(self.previous)
        self.directory.cleanup()

    def run_handoff(self):
        Path(recovery_boot.USB_RECOVERY_HANDOFF_PATH).write_text(json.dumps(self.marker))
        with patch.dict(sys.modules, self.modules), patch.object(recovery_boot, 'clear_recovery_request'):
            return recovery_boot.complete_usb_recovery_handoff()

    def test_verified_application_staged_before_core_confirmation(self):
        order = []
        self.app.stage_bundle.side_effect = lambda *args: (order.append('stage') or
            {'has_application': True, 'selected_paths': ['iotmd.py', 'app_settings.json'], 'version': 'alpha97'})
        self.partition.mark_app_valid_cancel_rollback.side_effect = lambda: order.append('confirm')
        self.assertTrue(self.run_handoff())
        self.assertEqual(order, ['stage', 'confirm'])
        self.assertFalse(Path(recovery_boot.USB_RECOVERY_HANDOFF_PATH).exists())
        self.assertFalse(recovery_boot.complete_usb_recovery_handoff())
        result = json.loads(Path(recovery_boot.USB_RECOVERY_RESULT_PATH).read_text())
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['application_sha256'], self.marker['application_sha256'])

    def test_wrong_version_slot_size_or_digest_never_stages(self):
        for key, value in [('core_version', 'old'), ('partition', 'ota_0'),
                           ('application_size', 1), ('application_sha256', '0'*64),
                           ('format_version', 2)]:
            previous = self.marker[key]
            self.marker[key] = value
            self.assertFalse(self.run_handoff())
            self.app.stage_bundle.assert_not_called()
            self.partition.mark_app_valid_cancel_rollback.assert_not_called()
            self.assertTrue(Path(recovery_boot.USB_RECOVERY_HANDOFF_PATH).exists())
            self.marker[key] = previous

    def test_signature_failure_is_retained_and_can_be_retried(self):
        self.app.stage_bundle.side_effect = ValueError('private exception details')
        self.assertFalse(self.run_handoff())
        self.assertNotIn('private', Path(recovery_boot.USB_RECOVERY_RESULT_PATH).read_text())
        self.partition.mark_app_valid_cancel_rollback.assert_not_called()
        self.app.stage_bundle.side_effect = None
        self.assertTrue(self.run_handoff())

    def test_provisioned_device_is_rejected(self):
        self.modules['credential_store'] = SimpleNamespace(is_provisioned=lambda: True)
        self.assertFalse(self.run_handoff())
        self.app.stage_bundle.assert_not_called()

    def test_incomplete_application_is_discarded(self):
        self.app.stage_bundle.return_value = {'has_application': True, 'selected_paths': ['iotmd.py']}
        self.assertFalse(self.run_handoff())
        self.app.discard_pending_update.assert_called_once()
        self.partition.mark_app_valid_cancel_rollback.assert_not_called()

    def test_settings_only_bundle_cannot_pass_as_complete_application(self):
        self.app.stage_bundle.return_value = {'has_application': True, 'selected_paths': ['app_settings.json']}
        self.assertFalse(self.run_handoff())
        self.app.discard_pending_update.assert_called_once()
        self.partition.mark_app_valid_cancel_rollback.assert_not_called()

    def test_uncommitted_upload_is_ignored(self):
        Path('.usb-recovery.json.tmp').write_text(json.dumps(self.marker))
        self.assertFalse(recovery_boot.complete_usb_recovery_handoff())
        self.app.stage_bundle.assert_not_called()
