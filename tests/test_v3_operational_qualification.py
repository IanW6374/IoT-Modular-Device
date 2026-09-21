import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from v3.runtime.iotmd_next.qualification import (
    OperationalQualification, QualificationError,
)
from v3.runtime.iotmd_next.storage import StorageContractError


ROOT = Path(__file__).resolve().parents[1]


class MemoryNamespace:
    def __init__(self):
        self.generation = 0
        self.payload = b''
        self.closed = False

    def snapshot(self):
        return self.generation, self.payload

    def commit(self, generation, payload):
        if generation != self.generation:
            raise RuntimeError('generation changed')
        self.generation += 1
        self.payload = bytes(payload)
        return self.generation

    def close(self):
        self.closed = True


class FullNamespace(MemoryNamespace):
    def __init__(self):
        super().__init__()
        self.commit_attempts = 0

    def commit(self, generation, payload):
        self.commit_attempts += 1
        raise StorageContractError('encrypted transactional storage is full')


class LimitedNamespace(MemoryNamespace):
    maximum = 4096

    def commit(self, generation, payload):
        if len(payload) > self.maximum:
            raise StorageContractError('encrypted transactional storage is full')
        return super().commit(generation, payload)


def profile(**changes):
    value = {
        'name': 'test',
        'minimum_soak_s': 60,
        'maximum_consecutive_unhealthy': 1,
        'minimum_health_samples': 1,
        'minimum_storage_samples': 1,
        'minimum_storage_free_bytes': 100,
        'maximum_network_recovery_s': 20,
        'required_network_recoveries': 1,
        'required_renewals': 1,
        'required_update_confirmations': 1,
        'required_power_recoveries': 1,
        'required_native_recoveries': 1,
        'required_watchdog_recoveries': 1,
        'required_identity_transactions': 1,
        'required_fleet_transactions': 1,
        'required_migration_rollbacks': 1,
        'required_driver_checks': 1,
    }
    value.update(changes)
    return value


class V3OperationalQualificationTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000]
        self.namespace = MemoryNamespace()
        self.history_namespace = MemoryNamespace()
        self.campaign_namespace = MemoryNamespace()
        self.release = {
            'version': '3.0.0-alpha.6', 'sequence': 2711,
            'confirmed': True,
        }
        self.recorder = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace,
            self.campaign_namespace
        )
        self.recorder.start()

    def test_untested_gates_are_not_reported_as_passed(self):
        result = self.recorder.snapshot()
        states = {item['name']: item['status'] for item in result['gates']}
        self.assertEqual(states['soak'], 'in-progress')
        self.assertEqual(states['storage'], 'not-run')
        self.assertEqual(states['network-recovery'], 'not-run')
        self.assertEqual(states['certificate-renewal'], 'not-run')
        self.assertEqual(states['release-confirmation'], 'passed')
        self.assertFalse(result['promotion_ready'])

    def test_health_retry_is_scoped_and_requires_a_new_observation_window(self):
        self.recorder.record_power_recovery(True)
        self.recorder.sample('failed', 50, True)
        self.recorder.sample('failed', 50, True)
        self.now[0] += 61
        self.recorder.sample('healthy', 200, True)
        result = self.recorder.restart_failed_gate('health', 'admin', 'MQTT fixed', 0)
        gates = {item['name']: item['status'] for item in result['gates']}
        self.assertEqual(gates['health'], 'not-run')
        self.assertEqual(gates['storage'], 'failed')
        self.assertEqual(gates['power-recovery'], 'passed')
        self.assertEqual(gates['soak'], 'passed')
        retry = self.recorder.retry_history()[-1]
        self.assertEqual(retry['actor'], 'admin')
        self.assertEqual(json.loads(retry['detail'])['counters']['maximum_consecutive_unhealthy'], 2)
        self.recorder.sample('healthy', 200, True)
        self.assertEqual(self.recorder.snapshot()['gates'][1]['status'], 'in-progress')
        self.now[0] += 61
        self.assertEqual(self.recorder.snapshot()['gates'][1]['status'], 'passed')
        with self.assertRaisesRegex(QualificationError, 'refresh'):
            self.recorder.restart_failed_gate('storage', 'admin', 'Space fixed', 0)

    def test_storage_retry_starts_fresh_window_and_preserves_health(self):
        self.recorder.sample('healthy', 50, True)
        self.now[0] += 61
        self.recorder.restart_failed_gate('storage', 'admin', 'Space reclaimed', 0)
        self.recorder.sample('healthy', 200, True)
        gates = {g['name']: g['status'] for g in self.recorder.snapshot()['gates']}
        self.assertEqual(gates['health'], 'passed')
        self.assertEqual(gates['storage'], 'in-progress')
        self.now[0] += 61
        gates = {g['name']: g['status'] for g in self.recorder.snapshot()['gates']}
        self.assertEqual(gates['storage'], 'passed')

    def test_paired_retry_without_campaign_cannot_erase_canary_evidence(self):
        recorder = OperationalQualification(self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace)
        recorder.start()
        recorder.record_update('failed')
        before = recorder.snapshot()
        with self.assertRaisesRegex(QualificationError, 'persistent campaign'):
            recorder.restart_failed_gate('paired-updates', 'admin', 'Trial repaired', 0)
        self.assertEqual(recorder.snapshot(), before)
        self.assertEqual(recorder.retry_generation(), 0)

    def test_campaign_retry_does_not_erase_unrelated_or_release_evidence(self):
        self.recorder.record_renewal(False)
        self.recorder.record_renewal(True)
        self.recorder.record_update('confirmed')
        before = self.recorder.snapshot()
        self.assertEqual(next(g for g in before['gates'] if g['name'] == 'certificate-renewal')['status'], 'failed')
        self.recorder.restart_failed_gate('certificate-renewal', 'admin', 'Renewal key fixed', 0)
        after = self.recorder.snapshot()
        self.assertEqual(after['counters']['renewal_attempts'], 0)
        self.assertEqual(after['counters']['update_confirmations'], before['counters']['update_confirmations'])
        self.recorder.record_renewal(True)
        restarted = OperationalQualification(self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace, self.campaign_namespace)
        self.assertEqual(next(g for g in restarted.start()['gates'] if g['name'] == 'certificate-renewal')['status'], 'passed')
        self.assertEqual(restarted.retry_generation(), 1)
        self.assertEqual(restarted.retry_history(), self.recorder.retry_history())

    def test_retry_refuses_to_clear_failure_without_durable_archive(self):
        self.recorder.record_power_recovery(False)
        before = self.recorder.snapshot()
        self.recorder._history_namespace = FullNamespace()
        with self.assertRaises(StorageContractError):
            self.recorder.restart_failed_gate('power-recovery', 'admin', 'Supply fixed', 0)
        self.assertEqual(self.recorder.snapshot(), before)
        self.assertEqual(self.recorder.retry_generation(), 0)

    def test_retry_trims_old_diagnostics_when_free_storage_is_below_capability(self):
        limited = LimitedNamespace()
        self.recorder._history_namespace = limited
        self.recorder.record_renewal(False)
        self.recorder.restart_failed_gate('certificate-renewal', 'admin', 'Key fixed', 0)
        # Only a minimal current summary plus one failure fits, despite the
        # advertised 4096-byte payload capability.
        minimal = dict(self.recorder._history)
        minimal['releases'] = []
        limited.maximum = len(json.dumps(minimal, sort_keys=True, separators=(',', ':')).encode())
        self.recorder._history['releases'] = [dict(self.recorder._history['current'])]
        self.recorder.record_renewal(False)
        self.recorder.record_power_recovery(True)
        self.recorder.restart_failed_gate('certificate-renewal', 'admin', 'Key fixed', 1)
        saved = json.loads(limited.payload)
        self.assertEqual(saved['releases'], [])
        self.assertEqual(len(saved['retries']), 1)
        self.assertEqual(saved['retry_generation'], 2)
        self.assertEqual(saved['retries'][0]['reason'], 'Key fixed')
        self.assertEqual(self.recorder.snapshot()['counters']['renewal_attempts'], 0)
        self.assertEqual(self.recorder.snapshot()['counters']['power_recoveries'], 1)
        restarted = OperationalQualification(self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), limited, self.campaign_namespace)
        restarted.start()
        self.assertEqual(restarted.retry_history(), saved['retries'])

    def test_failed_archive_compaction_preserves_committed_history_and_gate(self):
        self.recorder.record_renewal(False)
        self.recorder.restart_failed_gate('certificate-renewal', 'admin', 'Key fixed', 0)
        previous = json.loads(json.dumps(self.recorder._history))
        self.recorder.record_renewal(False)
        self.recorder._history_namespace = FullNamespace()
        with self.assertRaises(StorageContractError):
            self.recorder.restart_failed_gate('certificate-renewal', 'admin', 'Try again', 1)
        self.assertEqual(self.recorder._history, previous)
        self.assertEqual(self.recorder.snapshot()['counters']['renewal_failures'], 1)

    def test_failed_state_commit_preserves_failure_and_archived_request(self):
        self.recorder.record_power_recovery(False)
        before = self.recorder.snapshot()
        self.recorder._campaign_namespace = FullNamespace()
        with self.assertRaises(StorageContractError):
            self.recorder.restart_failed_gate('power-recovery', 'admin', 'Supply fixed', 0)
        self.assertEqual(self.recorder.snapshot(), before)
        self.assertEqual(len(self.recorder.retry_history()), 1)

    def test_retries_remain_within_native_namespace_capacity(self):
        for index in range(16):
            self.recorder.record_renewal(False)
            self.recorder.restart_failed_gate('certificate-renewal', 'admin', 'x' * 160, index)
            self.assertLessEqual(len(self.history_namespace.payload), 4096)
        self.assertLessEqual(len(self.recorder.retry_history()), 8)
        restarted = OperationalQualification(self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace, self.campaign_namespace)
        restarted.start()
        self.assertEqual(restarted.retry_generation(), 16)

    def test_previous_state_and_history_migrate_without_losing_failures(self):
        self.recorder.sample('failed', 50, True)
        self.recorder.sample('failed', 50, True)
        state = json.loads(self.namespace.payload)
        state['state_version'] = 2
        state.pop('gate_started_at')
        self.namespace.payload = json.dumps(state).encode()
        history = json.loads(self.history_namespace.payload)
        history['history_version'] = 1
        history.pop('retries')
        history.pop('retry_generation')
        self.history_namespace.payload = json.dumps(history).encode()
        restarted = OperationalQualification(self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace, self.campaign_namespace)
        self.assertEqual(restarted.start()['gates'][1]['status'], 'failed')
        self.assertEqual(restarted.retry_generation(), 0)

    def test_only_failed_gates_with_reason_can_be_restarted(self):
        for name in ('unknown', 'soak', 'health', 'release-confirmation'):
            with self.assertRaises(QualificationError):
                self.recorder.restart_failed_gate(name, 'admin', 'Retest', 0)
        self.recorder.sample('healthy', 200, True, canary_paused=True)
        with self.assertRaisesRegex(QualificationError, 'canary pause'):
            self.recorder.restart_failed_gate('canary-health', 'admin', 'Retest', 0)
        self.recorder.record_renewal(False)
        with self.assertRaises(QualificationError):
            self.recorder.restart_failed_gate('certificate-renewal', 'admin', ' ', 0)

    def test_close_releases_all_owned_namespaces(self):
        self.assertEqual(self.recorder.close(), 3)
        self.assertTrue(self.namespace.closed)
        self.assertTrue(self.history_namespace.closed)
        self.assertTrue(self.campaign_namespace.closed)
        with self.assertRaisesRegex(QualificationError, 'not started'):
            self.recorder.snapshot()

    def test_unconfirmed_release_cannot_be_promoted(self):
        self.release['confirmed'] = False
        result = self.recorder.snapshot()
        states = {item['name']: item['status'] for item in result['gates']}
        self.assertEqual(states['release-confirmation'], 'in-progress')
        self.assertFalse(result['promotion_ready'])

    def test_one_late_sample_does_not_qualify_the_soak(self):
        recorder = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release,
            profile(minimum_health_samples=2, minimum_storage_samples=2),
            self.history_namespace
        )
        recorder.reset()
        self.now[0] = 1060
        result = recorder.sample('healthy', 200, True)
        states = {item['name']: item['status'] for item in result['gates']}
        self.assertEqual(states['soak'], 'passed')
        self.assertEqual(states['health'], 'in-progress')
        self.assertEqual(states['storage'], 'in-progress')
        self.assertFalse(result['promotion_ready'])

    def test_complete_observed_campaign_unlocks_promotion(self):
        self.recorder.sample('healthy', 200, True, False)
        self.now[0] += 2
        self.recorder.sample('healthy', 190, False, False)
        self.now[0] += 10
        self.recorder.sample('healthy', 180, True, False)
        self.recorder.record_renewal(True)
        self.recorder.record_update('confirmed')
        self.recorder.record_power_recovery(True)
        for name in (
            'native-recovery', 'watchdog-recovery',
            'identity-interoperability', 'fleet-interoperability',
            'migration-rollback', 'driver-hardware',
        ):
            self.recorder.record_validation(name, True)
        self.now[0] = 1060
        result = self.recorder.sample('healthy', 170, True, False)
        self.assertTrue(result['promotion_ready'])
        self.assertTrue(all(
            item['status'] == 'passed' for item in result['gates']
        ))
        schema = json.loads((
            ROOT / 'v3/contracts/qualification-evidence.schema.json'
        ).read_text())
        Draft202012Validator(schema).validate(result)

    def test_failures_are_sticky_until_explicit_reset(self):
        self.recorder.sample('degraded', 200, True)
        self.now[0] += 1
        result = self.recorder.sample('failed', 50, True, True)
        states = {item['name']: item['status'] for item in result['gates']}
        self.assertEqual(states['health'], 'failed')
        self.assertEqual(states['storage'], 'failed')
        self.assertEqual(states['canary-health'], 'failed')
        self.recorder.record_renewal(False)
        self.recorder.record_update('rolled-back')
        self.recorder.record_power_recovery(False)
        self.recorder.record_validation('driver-hardware', False)
        states = {
            item['name']: item['status']
            for item in self.recorder.snapshot()['gates']
        }
        self.assertEqual(states['certificate-renewal'], 'failed')
        self.assertEqual(states['paired-updates'], 'in-progress')
        self.assertEqual(
            self.recorder.snapshot()['counters']['update_rollbacks'], 1
        )
        self.assertEqual(states['power-recovery'], 'failed')
        self.assertEqual(states['driver-hardware'], 'failed')
        reset = self.recorder.reset()
        self.assertEqual(reset['counters']['samples'], 0)
        self.assertEqual(
            next(item for item in reset['gates']
                 if item['name'] == 'power-recovery')['status'], 'not-run'
        )

    def test_network_recovery_time_and_open_outage_are_measured(self):
        self.recorder.sample('healthy', 200, True)
        self.now[0] += 1
        self.recorder.sample('healthy', 200, False)
        self.now[0] += 21
        open_outage = self.recorder.snapshot()
        self.assertTrue(open_outage['measurements']['network_outage_open'])
        self.assertEqual(
            next(item for item in open_outage['gates']
                 if item['name'] == 'network-recovery')['status'], 'failed'
        )
        recovered = self.recorder.sample('healthy', 200, True)
        self.assertEqual(recovered['counters']['network_recoveries'], 1)
        self.assertEqual(
            recovered['measurements']['maximum_network_recovery_s'], 21
        )

    def test_state_survives_restart_and_rejects_backward_time(self):
        self.recorder.sample('healthy', 200, True)
        restarted = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace
        )
        self.assertEqual(restarted.start()['counters']['samples'], 1)
        self.now[0] = 999
        with self.assertRaisesRegex(QualificationError, 'backwards'):
            restarted.sample('healthy', 200, True)

    def test_history_sidecar_does_not_change_current_state_contract(self):
        self.recorder.sample('healthy', 200, True)
        state = json.loads(self.namespace.payload.decode())
        self.assertEqual(state['state_version'], 3)
        self.assertNotIn('history', state)
        self.assertNotEqual(self.history_namespace.payload, b'')
        restarted = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace
        )
        result = restarted.start()
        self.assertEqual(result['counters']['samples'], 1)

    def test_full_history_sidecar_does_not_break_live_status(self):
        full_history = FullNamespace()
        recorder = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), full_history,
            self.campaign_namespace
        )
        recorder.start()
        result = recorder.sample('healthy', 200, True)
        self.assertEqual(result['counters']['samples'], 1)
        self.assertEqual(full_history.commit_attempts, 1)
        self.assertEqual(recorder.snapshot()['counters']['samples'], 1)
        self.assertEqual(full_history.commit_attempts, 1)

    def test_new_release_starts_a_fresh_evidence_campaign(self):
        self.recorder.sample('healthy', 200, True)
        self.release['version'] = '3.0.0-alpha.7'
        self.release['sequence'] = 2712
        restarted = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace,
            self.campaign_namespace
        )
        result = restarted.start()
        self.assertEqual(result['release']['version'], '3.0.0-alpha.7')
        self.assertEqual(result['counters']['samples'], 0)
        self.assertEqual(len(restarted.history()), 1)
        self.assertEqual(
            restarted.history()[0]['release_version'], '3.0.0-alpha.6'
        )
        self.assertIn(
            'release-confirmation', restarted.history()[0]['passed_gates']
        )

    def test_cross_release_evidence_survives_while_samples_restart(self):
        self.recorder.record_update('confirmed')
        self.recorder.record_power_recovery(True)
        self.recorder.record_renewal(True)
        self.release.update(version='3.0.0-alpha.7', sequence=2712)
        restarted = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release,
            profile(required_update_confirmations=2,
                    required_power_recoveries=2),
            self.history_namespace, self.campaign_namespace
        )
        result = restarted.start()
        self.assertEqual(result['counters']['samples'], 0)
        self.assertEqual(result['counters']['update_confirmations'], 1)
        self.assertEqual(result['counters']['power_recoveries'], 1)
        self.assertEqual(result['counters']['renewal_successes'], 1)
        states = {item['name']: item['status'] for item in result['gates']}
        self.assertEqual(states['paired-updates'], 'in-progress')
        self.assertEqual(states['canary-health'], 'not-run')
        restarted.record_update('confirmed')
        self.assertEqual(
            next(item for item in restarted.snapshot()['gates']
                 if item['name'] == 'paired-updates')['status'], 'passed'
        )

    def test_previous_release_history_is_bounded_and_survives_restart(self):
        recorder = self.recorder
        for number in range(7, 13):
            self.now[0] += 1
            self.release['version'] = '3.0.0-alpha.' + str(number)
            self.release['sequence'] += 1
            recorder = OperationalQualification(
                self.namespace, lambda: self.now[0], 'iot-md-001',
                lambda: self.release, profile(), self.history_namespace
            )
            recorder.start()
        history = recorder.history()
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]['release_version'], '3.0.0-alpha.8')
        restarted = OperationalQualification(
            self.namespace, lambda: self.now[0], 'iot-md-001',
            lambda: self.release, profile(), self.history_namespace
        )
        restarted.start()
        self.assertEqual(restarted.history(), history)


if __name__ == '__main__':
    unittest.main()
