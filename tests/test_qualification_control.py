import unittest

import qualification_control
from services.qualification_control_service import QualificationControlService


class QualificationControlTests(unittest.TestCase):
    def test_records_confirmed_controlled_observation(self):
        calls = []
        event = qualification_control.controlled_event({
            'gate': 'watchdog-recovery', 'outcome': 'success',
            'run_id': 'hil-001', 'confirm': True,
            'evidence_digest': 'sha256:' + 'a' * 64,
        }, 'automation', lambda *args: calls.append(args) or True)
        self.assertEqual(calls, [('watchdog-recovery', True)])
        self.assertEqual(event['run_id'], 'hil-001')

    def test_rejects_unconfirmed_or_automatic_gate(self):
        for value in (
            {'gate': 'watchdog-recovery', 'outcome': 'success', 'run_id': 'x'},
            {'gate': 'power-recovery', 'outcome': 'success', 'run_id': 'x',
             'confirm': True},
        ):
            with self.assertRaises(ValueError):
                qualification_control.controlled_event(
                    value, 'operator', lambda *_args: True
                )

    def test_scenarios_require_exact_phrase_and_alpha_build(self):
        value = qualification_control.scenario_request({
            'scenario': 'watchdog-recovery', 'run_id': 'hil-2',
            'confirmation': 'execute watchdog-recovery',
        }, 'operator', '3.0.0-alpha.37')
        self.assertTrue(value['disruptive'])
        with self.assertRaises(ValueError):
            qualification_control.scenario_request({
                'scenario': 'watchdog-recovery', 'run_id': 'hil-2',
                'confirmation': 'yes',
            }, 'operator', '3.0.0-alpha.37')
        with self.assertRaises(RuntimeError):
            qualification_control.scenario_request({
                'scenario': 'watchdog-recovery', 'run_id': 'hil-2',
                'confirmation': 'execute watchdog-recovery',
            }, 'operator', '3.0.0')

    def test_service_deduplicates_persisted_run_id(self):
        class Health:
            def __init__(self): self.events = []
            def snapshot(self): return {'events': list(self.events)}
            def record_event(self, kind, detail, values, **unused):
                self.events.append({'kind': kind, 'values': values})

        class Recorder:
            def __init__(self): self.calls = []
            def record_validation(self, *values):
                self.calls.append(values)
                return True

        health = Health()
        recorder = Recorder()
        service = QualificationControlService(
            recorder, health, lambda *_args: None, '3.0.0-alpha.37',
            lambda: object(), lambda _reason: None, lambda *_args: None,
        )
        payload = {
            'gate': 'watchdog-recovery', 'outcome': 'success',
            'run_id': 'same-run', 'confirm': True,
        }
        self.assertNotIn('duplicate', service.record(payload, 'rig'))
        self.assertTrue(service.record(payload, 'rig')['duplicate'])
        self.assertEqual(recorder.calls, [('watchdog-recovery', True)])

    def test_service_scenarios_are_guarded_and_do_not_record_success(self):
        calls = []
        service = QualificationControlService(
            object(), type('Health', (), {})(),
            lambda *values: calls.append(('log', values)), '3.0.0-alpha.37',
            lambda: object(), lambda reason: calls.append(('recovery', reason)),
            lambda *values: calls.append(('reset', values)),
        )
        result = service.scenario({
            'scenario': 'watchdog-recovery', 'run_id': 'wdt-1',
            'confirmation': 'execute watchdog-recovery',
        }, 'rig')
        self.assertEqual(result['scenario'], 'watchdog-recovery')
        self.assertFalse(service.should_feed_watchdog())
        self.assertFalse(any(item[0] == 'recovery' for item in calls))


if __name__ == '__main__':
    unittest.main()
