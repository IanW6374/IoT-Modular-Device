import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from update_operations import UpdateOperations, UpdateOperationRunner


class OperationRunnerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ops = UpdateOperations('device', str(Path(self.directory.name) / 'journal'), 'boot-one')
        self.policy = {'policy_sequence': 1, 'updates': {'channel': 'alpha'}, 'commands': [
            {'id': '%032x' % i, 'action': action, 'release_sequence': 2828, 'release_type': 'universal'}
            for i, action in enumerate(['check-update', 'download-update', 'activate-update'], 1)]}
        self.identifier = self.ops.prepare(self.policy)
        self.ops.transition('accepted')
        self.fleet = SimpleNamespace(state={'policy': self.policy}, within_maintenance_window=lambda: True)
        self.check = AsyncMock(return_value='Release found')
        self.download = AsyncMock()
        self.activate = Mock(return_value='Rebooting')
        self.ready = Mock(return_value=True)
        self.cancellation = Mock(return_value={'status': 'cancelled'})
        self.runner = UpdateOperationRunner(self.ops, self.fleet, self.check, self.download,
                                           self.activate, self.ready, self.cancellation)

    async def test_single_worker_checks_stages_then_records_intent_before_activation(self):
        self.activate.side_effect = lambda _: self.assertEqual(self.ops.active()['state'], 'installing')
        await self.runner.tick()
        self.check.assert_awaited_once_with('alpha', 2828, 'universal')
        self.download.assert_awaited_once()
        self.activate.assert_called_once()
        for _ in range(5): await self.runner.tick()
        self.assertEqual(self.check.await_count, 1)
        self.assertEqual(self.activate.call_count, 1)
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'installing')

    async def test_already_installed_rejected_before_download(self):
        self.check.return_value = 'No newer compatible release: already installed'
        with self.assertRaises(ValueError): await self.runner.tick()
        self.download.assert_not_awaited()
        self.activate.assert_not_called()
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'failed')

    async def test_cancel_at_check_yield_never_downloads_or_activates(self):
        async def cancel(*args): self.ops.transition('cancelling')
        self.check.side_effect = cancel
        await self.runner.tick()
        self.download.assert_not_awaited()
        self.activate.assert_not_called()
        await self.runner.tick()
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'cancelled')

    async def test_cancel_at_download_yield_waits_for_safe_worker_ack(self):
        async def cancel(): self.ops.transition('cancelling')
        self.download.side_effect = cancel
        await self.runner.tick()
        self.activate.assert_not_called()
        self.cancellation.return_value = {'status': 'cancelling'}
        await self.runner.tick()
        self.assertEqual(self.ops.active()['state'], 'cancelling')
        self.cancellation.return_value = {'status': 'cancelled'}
        await self.runner.tick()
        self.assertIsNone(self.ops.active())

    async def test_staging_failure_is_terminal_and_not_replayed(self):
        self.download.side_effect = ValueError('Signature verification failed')
        with self.assertRaises(ValueError): await self.runner.tick()
        await self.runner.tick()
        self.assertEqual(self.download.await_count, 1)
        self.activate.assert_not_called()
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'failed')

    async def test_lost_activation_ack_is_unresolved_not_a_repeated_activation(self):
        self.activate.side_effect = OSError('Activation acknowledgement lost')
        with self.assertRaises(OSError): await self.runner.tick()
        await self.runner.tick()
        self.assertEqual(self.activate.call_count, 1)
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'interrupted')

    async def test_schedule_wait_does_not_repeat_staging(self):
        self.fleet.within_maintenance_window = lambda: False
        await self.runner.tick()
        await self.runner.tick()
        self.assertEqual(self.download.await_count, 1)
        self.assertEqual(self.ops.active()['state'], 'scheduled')
        self.fleet.within_maintenance_window = lambda: True
        await self.runner.tick()
        self.activate.assert_called_once()

    async def test_stage_only_has_no_activation(self):
        self.ops.transition('failed')
        self.policy['policy_sequence'] = 2
        self.policy['commands'] = self.policy['commands'][:2]
        self.policy['commands'][0]['id'] = 'f'*32
        self.identifier = self.ops.prepare(self.policy)
        self.ops.transition('accepted')
        await self.runner.tick()
        await self.runner.tick()
        self.assertEqual(self.ops.active()['state'], 'staged')
        self.activate.assert_not_called()

    async def test_reboot_without_verified_staged_components_is_unresolved(self):
        self.fleet.within_maintenance_window = lambda: False
        await self.runner.tick()
        self.ready.return_value = False
        self.runner.recover(2827, 2827, True)
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'interrupted')
        self.activate.assert_not_called()

    async def test_recovery_after_confirmed_boot_completes_without_replaying(self):
        await self.runner.tick()
        self.runner.recover(2828, 2828, True)
        await self.runner.tick()
        self.assertEqual(self.ops.snapshot(self.identifier)['state'], 'complete')
        self.assertEqual(self.activate.call_count, 1)

