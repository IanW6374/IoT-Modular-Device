import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from api_operations import OperationJournal, OperationError, MAX_OPERATIONS
from api_operation_fixtures import MemoryNamespace


class OperationJournalTests(unittest.TestCase):
    client = 'a' * 64
    other = 'b' * 64

    def setUp(self):
        patcher = mock.patch('api_operations.os.sync')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = str(Path(self.temp.name) / 'operations')
        self.storage = MemoryNamespace()
        self.journal = self.reopen('boot-1')

    def reopen(self, boot):
        return OperationJournal(lambda: self.storage, self.directory, boot)

    def reserve(self, sequence=1, body=b'{}'):
        return self.journal.reserve(self.client, str(sequence) + '.0123456789abcdef',
            'POST', '/api/v3/configuration/restart', body)

    def test_completed_response_survives_restart_and_replays(self):
        record, replay = self.reserve()
        self.assertFalse(replay)
        self.journal.finish(record, 202, {'accepted': True})
        self.journal = self.reopen('boot-2')
        same, replay = self.reserve()
        self.assertTrue(replay)
        self.assertEqual(same['id'], record['id'])
        status, result = self.journal.result(same['id'], self.client)
        self.assertEqual(status, 202)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['operation']['status'], 'complete')
        self.assertEqual(self.journal.next_sequence(self.client), 2)

    def test_changed_payload_is_conflict_not_new_operation(self):
        self.reserve()
        with self.assertRaises(OperationError) as caught:
            self.reserve(body=b'{"different":true}')
        self.assertEqual(caught.exception.code, 'idempotency_conflict')
        self.assertEqual(len(self.journal.state['records']), 1)

    def test_pending_request_is_interrupted_on_restart(self):
        record, _ = self.reserve()
        self.journal = self.reopen('boot-2')
        self.assertEqual(self.journal.operation(record['id'], self.client)['status'], 'interrupted')
        self.assertTrue(self.reserve()[1])
        with self.assertRaises(OperationError) as caught:
            self.journal.result(record['id'], self.client)
        self.assertEqual(caught.exception.code, 'operation_interrupted')

    def test_evicted_key_cannot_execute_again(self):
        first = None
        for number in range(1, MAX_OPERATIONS + 2):
            record, _ = self.reserve(number)
            first = first or record
            self.journal.finish(record, 200, {'ok': True})
        self.assertEqual(len(self.journal.state['records']), MAX_OPERATIONS)
        self.assertFalse(Path(self.directory, first['id'] + '.json').exists())
        with self.assertRaises(OperationError) as caught:
            self.reserve()
        self.assertEqual(caught.exception.code, 'request_sequence_expired')

    def test_all_active_operations_apply_backpressure(self):
        for number in range(1, MAX_OPERATIONS + 1):
            self.reserve(number)
        with self.assertRaises(OperationError) as caught:
            self.reserve(MAX_OPERATIONS + 1)
        self.assertEqual(caught.exception.code, 'operation_limit')
        self.assertEqual(self.journal.next_sequence(self.client), MAX_OPERATIONS + 1)

    def test_failed_reservation_does_not_advance_memory_watermark(self):
        self.storage.fail = True
        with self.assertRaises(OSError):
            self.reserve()
        self.assertEqual(self.journal.next_sequence(self.client), 1)
        self.assertFalse(self.journal.state['records'])
        self.assertGreater(self.storage.closes, 1)

    def test_result_write_failure_keeps_reservation(self):
        record, _ = self.reserve()
        with mock.patch('api_operations.os.rename', side_effect=OSError('power loss')):
            with self.assertRaises(OSError):
                self.journal.finish(record, 200, {'ok': True})
        self.journal = self.reopen('boot-2')
        self.assertEqual(self.journal.operation(record['id'], self.client)['status'], 'interrupted')
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_operations_and_results_are_certificate_scoped(self):
        record, _ = self.reserve()
        for callback in (self.journal.operation, self.journal.result):
            with self.assertRaises(OperationError) as caught:
                callback(record['id'], self.other)
            self.assertEqual(caught.exception.status, 404)

    def test_invalid_storage_fails_closed(self):
        self.storage.payload = b'invalid JSON'
        with self.assertRaises(OperationError):
            self.reopen('boot-2')

    def test_large_result_update_replaces_instead_of_double_counting(self):
        record, _ = self.reserve()
        payload = {'data': 'x' * (380 * 1024)}
        self.journal.finish(record, 200, payload)
        self.journal.finish(record, 200, payload)

    def test_large_backups_prune_terminal_results_without_reexecution(self):
        for number in range(1, 5):
            record, _ = self.reserve(number)
            self.journal.finish(record, 200, {'data': 'x' * (380 * 1024)})
        self.assertLessEqual(len(self.journal.state['records']), 2)
        with self.assertRaises(OperationError) as caught:
            self.reserve()
        self.assertEqual(caught.exception.code, 'request_sequence_expired')

    def test_invalid_keys_are_rejected_without_storage_write(self):
        for key in ('', '1', '0.0123456789abcdef', '1.BADNONCE',
                    '9007199254740992.0123456789abcdef'):
            with self.subTest(key=key), self.assertRaises(OperationError):
                self.journal.reserve(self.client, key, 'POST', '/api/v3/device', b'{}')
        self.assertEqual(self.storage.generation, 0)

    def test_request_content_is_not_persisted_in_journal(self):
        self.reserve(body=b'{"password":"very-private-value"}')
        self.assertNotIn(b'very-private-value', self.storage.payload)
        self.assertEqual(len(json.loads(self.storage.payload)['records'][0]['digest']), 64)

    def test_corrupt_result_fails_closed_without_consuming_another_sequence(self):
        record, _ = self.reserve()
        self.journal.finish(record, 200, {'ok': True})
        for content in (b'not-json', b'[]', b'null', b'\xff'):
            with self.subTest(content=content):
                Path(self.directory, record['id'] + '.json').write_bytes(content)
                with self.assertRaises(OperationError) as caught:
                    self.journal.result(record['id'], self.client)
                self.assertEqual(caught.exception.code, 'result_invalid')
                self.assertEqual(caught.exception.status, 503)
                self.assertTrue(self.reserve()[1])
                self.assertEqual(self.journal.next_sequence(self.client), 2)

    def test_queued_command_after_restart_is_uncertain_not_replayed(self):
        record, _ = self.journal.reserve(self.client, '1.0123456789abcdef',
            'POST', '/api/v3/modules/0001/commands', b'{"command":"on"}')
        self.journal.finish(record, 202, {'accepted': True}, state='queued')
        self.journal = self.reopen('boot-2')
        self.assertEqual(self.journal.operation(record['id'], self.client)['completion_scope'], 'module_command')
        with self.assertRaises(OperationError) as caught:
            self.journal.result(record['id'], self.client)
        self.assertEqual(caught.exception.code, 'operation_interrupted')

    def test_record_cannot_survive_with_a_rolled_back_watermark(self):
        self.reserve(sequence=2)
        state = json.loads(self.storage.payload)
        state['clients'][self.client] = 1
        self.storage.payload = json.dumps(state).encode()
        with self.assertRaises(OperationError) as caught:
            self.reopen('boot-2')
        self.assertEqual(caught.exception.code, 'journal_invalid')
