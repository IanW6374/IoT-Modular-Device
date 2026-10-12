import tempfile
import unittest
from pathlib import Path
from unittest import mock

import update_operations as module
from update_operations import UpdateOperations, PHASES, SLOT_BYTES, RETAINED, operation_plan


class UpdateOperationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'operations')
        self.ops = UpdateOperations('device-1', self.path, 'boot-one')

    def policy(self, sequence=1, activation=True):
        return {'policy_sequence': sequence, 'commands': [
            {'id': '%032x' % (sequence * 10 + index), 'action': action,
             'release_sequence': 2828, 'release_type': 'universal'}
            for index, action in enumerate(['check-update', 'download-update'] +
                (['activate-update'] if activation else []))]}

    def admit(self, sequence=1):
        identifier = self.ops.prepare(self.policy(sequence))
        self.ops.transition('accepted', detail='Signed admission committed')
        return identifier

    def staged(self):
        self.ops.transition('checking', 'inspect')
        self.ops.progress('core_write', 20, ['queued', 'inspect'])
        self.ops.progress('core_verify', 100, ['queued', 'inspect', 'core_write'])
        self.ops.progress('application_download', 20, list(PHASES[:4]))
        self.ops.progress('application_verify', 100, list(PHASES[:5]))
        self.ops.transition('staged', 'pair', completed=PHASES[:7])

    def restart(self):
        self.ops = UpdateOperations('device-1', self.path, 'boot-two')

    def test_capacity_is_reserved_before_admission_and_bounded(self):
        self.ops.open()
        before = [Path(self.path + '.' + str(i)).stat().st_size for i in (0, 1)]
        self.assertEqual(before, [SLOT_BYTES] * 2)
        for seq in range(1, 20):
            self.admit(seq)
            self.ops.transition('failed', detail='Rejected before staging')
        self.assertEqual(len(self.ops.state['records']), RETAINED)
        self.assertEqual(self.ops.state['watermark'], 19)
        self.assertEqual([Path(self.path + '.' + str(i)).stat().st_size for i in (0, 1)], before)

    def test_no_capacity_no_admission(self):
        with mock.patch.object(module, '_flush', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.admit()
        self.assertEqual(self.ops.state['records'], [])

    def test_percentages_do_not_flush_or_complete_verification(self):
        identifier = self.admit()
        self.ops.transition('checking', 'inspect')
        self.ops.progress('core_write', 0, ['queued', 'inspect'])
        generation = self.ops.state['generation']
        for percent in range(101):
            self.ops.progress('core_write', percent, ['queued', 'inspect'])
        self.assertEqual(self.ops.state['generation'], generation)
        value = self.ops.snapshot(identifier)
        self.assertEqual(value['percent'], 100)
        self.assertNotIn('core_write', value['completed'])
        self.assertEqual(value['sample_sequence'], 102)

    def test_reboot_loses_only_volatile_percent_not_identity_or_stage(self):
        identifier = self.admit()
        self.ops.transition('checking', 'inspect')
        self.ops.progress('core_write', 90, ['queued', 'inspect'])
        self.restart()
        value = self.ops.snapshot(identifier)
        self.assertEqual((value['phase'], value['boot_id'], value['percent']), ('core_write', 'boot-two', None))
        self.ops.recover_execution(2827, 2827, True)
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'interrupted')
        self.assertFalse(self.ops.command_allowed(self.policy()['commands'][1]))

    def test_health_confirmed_exact_pair_completes_retained_operation(self):
        identifier = self.admit()
        self.staged()
        self.ops.transition('installing', 'install')
        self.restart()
        self.ops.recover_execution(2828, 2828, True)
        value = self.ops.snapshot(identifier)
        self.assertEqual(value['state'], 'complete')
        self.assertEqual(value['completed'], list(PHASES))
        self.admit(2)
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'complete')

    def test_matching_versions_without_install_intent_are_not_success(self):
        identifier = self.admit()
        self.restart()
        self.ops.recover_execution(2828, 2828, True)
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'accepted')

    def test_newer_release_or_partial_confirmation_is_not_this_job_success(self):
        for app, core, idle in ((2829, 2829, True), (2828, 2827, True), (2828, 2828, False)):
            with self.subTest(app=app, core=core, idle=idle):
                identifier = self.admit(self.ops.state['watermark'] + 1)
                self.staged()
                self.ops.transition('installing', 'install')
                self.ops.recover_execution(app, core, idle)
                self.assertEqual(self.ops.snapshot(identifier)['state'], 'interrupted')

    def test_prepared_admission_requires_matching_committed_signed_policy(self):
        identifier = self.ops.prepare(self.policy())
        self.assertFalse(self.ops.command_allowed(self.policy()['commands'][0]))
        self.restart()
        self.ops.recover_admission(self.policy())
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'accepted')
        self.assertTrue(self.ops.command_allowed(self.policy()['commands'][0]))

    def test_uncommitted_admission_does_not_dispatch_after_reboot(self):
        identifier = self.ops.prepare(self.policy())
        self.restart()
        self.ops.recover_admission(None)
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'interrupted')

    def test_duplicate_id_or_evicted_sequence_cannot_repeat_effects(self):
        identifier = self.admit()
        self.ops.transition('failed')
        with self.assertRaises(ValueError): self.ops.prepare(self.policy())
        policy = self.policy(2)
        policy['commands'][0]['id'] = identifier
        with self.assertRaises(ValueError): self.ops.prepare(policy)
        for seq in range(2, 9):
            self.admit(seq)
            self.ops.transition('failed')
        with self.assertRaises(KeyError): self.ops.snapshot(identifier)
        with self.assertRaises(ValueError): self.ops.prepare(self.policy())

    def test_second_operation_cannot_overwrite_active_or_staged_operation(self):
        self.admit()
        with self.assertRaises(ValueError): self.ops.prepare(self.policy(2))
        self.staged()
        with self.assertRaises(ValueError): self.ops.prepare(self.policy(2))
        with self.assertRaises(ValueError): self.ops.prepare({'commands': []})

    def test_cancellation_requires_safe_ack_before_terminal_result(self):
        identifier = self.admit()
        self.ops.transition('cancelling')
        self.assertFalse(self.ops.command_allowed(self.policy()['commands'][1]))
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'cancelling')
        with self.assertRaises(ValueError): self.ops.transition('staging', 'core_write')
        self.ops.transition('cancelled', detail='Safely stopped')
        self.restart()
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'cancelled')

    def test_irreversible_installation_cannot_be_cancelled_or_replayed(self):
        self.admit()
        self.staged()
        self.ops.transition('installing', 'install')
        with self.assertRaises(ValueError): self.ops.transition('cancelling')
        self.assertFalse(self.ops.command_allowed(self.policy()['commands'][2]))

    def test_stage_and_state_cannot_regress_or_skip_installation(self):
        self.admit()
        with self.assertRaises(ValueError): self.ops.transition('complete', 'complete')
        with self.assertRaises(ValueError): self.ops.transition('installing', 'install')
        self.staged()
        with self.assertRaises(ValueError): self.ops.transition('staging', 'core_write')

    def test_snapshot_is_read_only_defensive_and_contains_no_signed_material(self):
        identifier = self.admit()
        with mock.patch.object(self.ops, '_commit', side_effect=AssertionError('Snapshot wrote storage')):
            value = self.ops.snapshot(identifier)
        value['completed'].clear()
        self.assertEqual(self.ops.snapshot(identifier)['completed'], ['queued'])
        self.assertNotIn('signature', value)
        self.assertNotIn('key', value)

    def test_torn_alternate_slot_preserves_previous_valid_generation(self):
        identifier = self.admit()
        expected = self.ops.snapshot(identifier)
        alternate = 1 - self.ops.slot
        with open(self.path + '.' + str(alternate), 'r+b') as stream:
            stream.write(b'123:bad\npartial')
        self.restart()
        self.assertEqual(self.ops.snapshot(identifier)['revision'], expected['revision'])

    def test_both_bad_slots_fail_closed_not_empty(self):
        self.admit()
        for slot in (0, 1):
            with open(self.path + '.' + str(slot), 'r+b') as stream: stream.write(b'bad\n')
        self.restart()
        with self.assertRaises(RuntimeError): self.ops.prepare(self.policy(2))

    def test_ambiguous_flush_reloads_disk_before_another_transition(self):
        identifier = self.admit()
        with mock.patch.object(module, '_flush', side_effect=OSError('Flush acknowledgement lost')):
            with self.assertRaises(OSError): self.ops.transition('checking', 'inspect')
        self.assertFalse(self.ops.loaded)
        self.assertEqual(self.ops.snapshot(identifier)['state'], 'checking')

    def test_plan_requires_typed_exact_signed_release_and_stable_id(self):
        for change in ('id', 'release_sequence', 'release_type', 'action'):
            policy = self.policy()
            policy['commands'][0][change] = {'id': 'short', 'release_sequence': 0,
                'release_type': '', 'action': 'rollback'}[change]
            with self.assertRaises(ValueError): operation_plan(policy)
        policy = self.policy()
        policy['commands'][1]['release_sequence'] += 1
        with self.assertRaises(ValueError): operation_plan(policy)


if __name__ == '__main__':
    unittest.main()
