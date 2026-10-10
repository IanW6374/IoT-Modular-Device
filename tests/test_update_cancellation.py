import unittest
from unittest.mock import Mock

from update_cancellation import UpdateCancellation


class UpdateCancellationTests(unittest.TestCase):
    def setUp(self):
        self.upload = Mock()
        self.upload.installing.return_value = False
        self.downloads = Mock()
        self.downloads.download_active.return_value = False
        self.fleet = Mock(state={'policy': {'commands': [
            {'release_sequence': 123, 'release_type': 'universal'}]}})
        self.fleet.cancel_updates.side_effect = lambda seq, kind: self.fleet.state.update(
            update_cancelled={'release_sequence': seq, 'release_type': kind})
        self.components = [Mock(), Mock(), Mock()]
        for component in self.components:
            component.update_status.return_value = {'status': 'idle'}
        self.orchestrator = Mock()
        self.orchestrator.load.return_value = {}
        self.telemetry = Mock(progress={})
        self.control = UpdateCancellation(self.upload, self.downloads, self.fleet,
            self.components, self.orchestrator, self.telemetry)

    def test_staging_is_signalled_without_deleting_active_artifacts(self):
        self.upload.installing.return_value = True
        result = self.control.cancel()
        self.assertEqual(result['status'], 'cancelling')
        self.upload.cancel.assert_called_once()
        self.upload.discard_staged.assert_not_called()
        self.downloads.discard_update.assert_not_called()
        self.upload.installing.return_value = False
        self.assertEqual(self.control.status()['status'], 'cancelled')
        self.upload.discard_staged.assert_not_called()  # Status reads never mutate.

    def test_download_cancellation_defers_cleanup_to_the_running_coroutine(self):
        self.downloads.download_active.return_value = True
        self.assertEqual(self.control.cancel()['status'], 'cancelling')
        self.downloads.discard_update.assert_called_once_with(self.upload.discard_staged)
        self.upload.discard_staged.assert_not_called()

    def test_idle_staged_update_is_discarded_and_planned_release_cleared(self):
        self.assertEqual(self.control.cancel()['status'], 'cancelled')
        self.upload.discard_staged.assert_called_once()
        self.orchestrator.clear.assert_called_once()
        self.assertEqual(self.telemetry.progress, {})

    def test_unremoved_ready_state_is_not_falsely_acknowledged(self):
        self.fleet.state['update_cancelled'] = {'release_sequence': 123, 'release_type': 'universal'}
        self.components[2].update_status.return_value = {'status': 'ready'}
        self.assertEqual(self.control.status()['status'], 'cancelling')

    def test_activation_and_wrong_release_are_rejected_without_side_effects(self):
        for status in ('activating', 'trial', 'committing'):
            with self.subTest(status=status):
                self.components[2].update_status.return_value = {'status': status}
                with self.assertRaisesRegex(ValueError, 'Installation has begun'):
                    self.control.cancel()
        self.components[2].update_status.return_value = {'status': 'idle'}
        with self.assertRaisesRegex(ValueError, 'not this device'):
            self.control.cancel({'release_sequence': 124, 'release_type': 'universal'})
        self.fleet.cancel_updates.assert_not_called()
        self.upload.cancel.assert_not_called()

    def test_orchestrator_activation_also_blocks_cancellation(self):
        self.orchestrator.load.return_value = {'status': 'activating'}
        with self.assertRaisesRegex(ValueError, 'Installation has begun'):
            self.control.cancel()

    def test_old_policy_cannot_cancel_a_different_live_or_staged_release(self):
        request = {'release_sequence': 123, 'release_type': 'universal'}
        self.downloads.download_active.return_value = True
        self.telemetry.progress = {'release_sequence': 124, 'type': 'universal'}
        with self.assertRaisesRegex(ValueError, 'not this device'):
            self.control.cancel(request)
        self.downloads.download_active.return_value = False
        self.components[2].update_status.return_value = {'status': 'ready', 'release_sequence': 124}
        with self.assertRaisesRegex(ValueError, 'different release'):
            self.control.cancel(request)
        self.components[2].update_status.return_value = {'status': 'idle'}
        self.upload.installing.return_value = True
        with self.assertRaisesRegex(ValueError, 'browser upload'):
            self.control.cancel(request)
        self.fleet.cancel_updates.assert_not_called()


if __name__ == '__main__':
    unittest.main()
