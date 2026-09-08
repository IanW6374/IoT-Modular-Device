import unittest

from alpha_qualification import AlphaQualificationService


class Recorder:
    def __init__(self):
        self.started = 0
        self.samples = []
        self.updates = []
        self.renewals = []
        self.power = []
        self.validations = []

    def start(self):
        self.started += 1

    def sample(self, *values):
        self.samples.append(values)
        return self.snapshot()

    def record_update(self, outcome):
        self.updates.append(outcome)

    def record_renewal(self, successful):
        self.renewals.append(successful)

    def record_power_recovery(self, successful):
        self.power.append(successful)

    def record_validation(self, name, successful):
        self.validations.append((name, successful))

    def history(self):
        return [{
            'release_version': '3.0.0-alpha.16',
            'passed_gates': ['soak'], 'failed_gates': [],
            'promotion_ready': False,
        }]

    def snapshot(self):
        return {
            'promotion_ready': False,
            'gates': [
                {'name': 'soak', 'status': 'in-progress'},
                {'name': 'power-recovery', 'status': 'not-run'},
            ],
        }


class AlphaQualificationTests(unittest.TestCase):
    def test_lazy_recorder_reports_and_records_observations(self):
        recorder = Recorder()
        service = AlphaQualificationService(
            'device', lambda: {}, lambda: 1,
            lambda clock, device, release: recorder
        )
        self.assertEqual(service.status()['summary'], 'In progress')
        self.assertEqual(recorder.started, 1)
        service.observe('healthy', 1000, True)
        service.record_update('confirmed')
        service.record_renewal(True)
        service.record_power_recovery(True)
        service.record_validation('driver-hardware', True)
        self.assertEqual(recorder.samples, [('healthy', 1000, True, False)])
        self.assertEqual(recorder.updates, ['confirmed'])
        self.assertEqual(recorder.renewals, [True])
        self.assertEqual(recorder.power, [True])
        self.assertEqual(recorder.validations, [('driver-hardware', True)])
        status = service.status()
        self.assertEqual(status['gate_sources']['soak'], 'device-observed')
        self.assertEqual(
            status['gate_sources']['power-recovery'], 'device-observed'
        )
        self.assertEqual(status['history'][0]['release_version'],
                         '3.0.0-alpha.16')

    def test_healthy_power_on_after_healthy_boot_is_recorded_once(self):
        recorder = Recorder()
        service = AlphaQualificationService(
            'device', lambda: {}, lambda: 1,
            lambda clock, device, release: recorder
        )
        previous = {
            'boot_count': 7, 'reset_cause': 'soft_reset',
            'healthy': True, 'stage': 'running',
        }
        current = {
            'boot_count': 8, 'reset_cause': 'pwron_reset',
            'healthy': True, 'stage': 'running',
        }

        self.assertTrue(service.record_successful_boot(current, previous))
        self.assertFalse(service.record_successful_boot(current, previous))
        self.assertEqual(recorder.power, [True])

    def test_non_power_or_unhealthy_boot_is_not_qualification_evidence(self):
        recorder = Recorder()
        service = AlphaQualificationService(
            'device', lambda: {}, lambda: 1,
            lambda clock, device, release: recorder
        )
        previous = {'boot_count': 2, 'healthy': True, 'stage': 'running'}
        current = {
            'boot_count': 3, 'reset_cause': 'soft_reset',
            'healthy': True, 'stage': 'running',
        }
        self.assertFalse(service.record_successful_boot(current, previous))
        current['reset_cause'] = 'pwron_reset'
        current['healthy'] = False
        self.assertFalse(service.record_successful_boot(current, previous))
        previous['healthy'] = False
        current['healthy'] = True
        self.assertFalse(service.record_successful_boot(current, previous))
        self.assertEqual(recorder.power, [])

    def test_unavailable_recorder_is_fail_closed(self):
        service = AlphaQualificationService(
            'device', lambda: {}, lambda: 1,
            lambda *args: (_ for _ in ()).throw(RuntimeError('no platform'))
        )
        status = service.status()
        self.assertFalse(status['available'])
        self.assertEqual(status['summary'], 'Unavailable')
        self.assertIn('no platform', status['error'])

    def test_missing_native_core_has_actionable_error(self):
        service = AlphaQualificationService(
            'device', lambda: {}, lambda: 1,
            lambda *args: (_ for _ in ()).throw(
                RuntimeError('native v3 platform is unavailable')
            )
        )
        status = service.status()
        self.assertIn('install the universal release', status['error'])

    def test_native_update_state_distinguishes_mechanism_and_qualification(self):
        class Platform:
            def capabilities(self):
                return {
                    'updates': {
                        'native_pair_journal': True,
                        'native_trial_observation': True,
                        'native_trial_control': True,
                        'paired_trial': False,
                        'native_rollback': False,
                    },
                    'recovery': {
                        'product_independent': True, 'qualified': False,
                    },
                    'jobs': {'async_worker': True, 'qualified': False},
                    'resources': {
                        'managed': True, 'physical': True,
                        'shared_buses': True, 'interrupt_cleanup': True,
                        'soft_restart_cleanup': True, 'recovery': True,
                        'qualified': False,
                        'kinds': ['adc', 'gpio', 'i2c', 'spi', 'uart'],
                    },
                }

            def update_snapshot(self):
                return {
                    'running_label': 'ota_0', 'running_state': 'valid',
                    'next_label': 'ota_1', 'pending_verify': False,
                    'can_confirm': False, 'can_rollback': False,
                }

            def pair_snapshot(self):
                return {
                    'phase': 'idle', 'sequence': 0, 'pair_id': '',
                    'platform_label': '', 'runtime_slot': '',
                    'previous_runtime_slot': '', 'runtime_healthy': False,
                    'failure': '',
                }

            def recovery_snapshot(self):
                return {'requested': False, 'failed_boots': 0}

        service = AlphaQualificationService(
            'device', lambda: {}, lambda: 1, lambda *args: Recorder()
        )
        service.platform = Platform()
        native = service.status()['native_update']
        self.assertTrue(native['control_available'])
        self.assertTrue(native['pair_journal_available'])
        self.assertFalse(native['paired_trial_qualified'])
        self.assertTrue(native['recovery_available'])
        self.assertTrue(native['jobs_available'])
        self.assertTrue(native['resources_available'])
        self.assertFalse(native['resources_qualified'])
        self.assertEqual(native['snapshot']['running_label'], 'ota_0')

    def test_missing_storage_is_not_reported_as_zero_free_bytes(self):
        value = AlphaQualificationService.observation('', False, {}, False)
        self.assertIsNone(value['storage_free_bytes'])


if __name__ == '__main__':
    unittest.main()
