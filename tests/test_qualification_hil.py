import unittest

from v3.host.qualification_hil import native


class QualificationHILTests(unittest.TestCase):
    def test_native_records_success_only_after_observed_recovery_and_return(self):
        class Clock:
            def __init__(self):
                self.values = iter((0, 1, 2, 70, 80))
            def __call__(self):
                return next(self.values)

        class Client:
            def __init__(self):
                self.started = False
                self.boot_reads = 0
                self.events = []
            def get(self, path):
                if path == '/api/v2/services':
                    self.boot_reads += 1
                    if self.started and self.boot_reads == 2:
                        raise OSError('device is in recovery')
                    return {'services': {'boot': {
                        'boot_count': 12 if self.started else 10,
                    }}}
                if path == '/api/v2/device':
                    return {'device': {'qualification_observation': {
                        'health_state': 'healthy',
                    }}}
                return {'qualification': {
                    'release': {'version': '3.0.0-alpha.54'},
                    'native_update': {'recovery': {
                        'boot_count': 102 if self.started else 100,
                    }},
                }}
            def post(self, path, value):
                if path.endswith('/native-recovery'):
                    self.started = True
                    return {'accepted': True}
                self.events.append(value)
                return {'accepted': True, 'event': value}

        client = Client()
        result = native(
            client, 'native-a54-001', 120, minimum_recovery_s=60,
            clock=Clock(), sleeper=lambda _seconds: None,
        )

        self.assertEqual(result['event']['gate'], 'native-recovery')
        self.assertEqual(result['event']['outcome'], 'success')
        self.assertEqual(result['event']['run_id'], 'native-a54-001')


if __name__ == '__main__':
    unittest.main()
