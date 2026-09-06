import unittest

from v3.runtime.iotmd_next.bootstrap import ProductBootstrap, BootstrapError


class Composition:
    def __init__(self):
        self.booted = None
        self.polls = 0
        self.stopped = False

    def boot(self, configuration):
        self.booted = configuration
        return {'mode': 'compatibility'}

    def poll(self):
        self.polls += 1

    def stop(self):
        self.stopped = True

    def snapshot(self):
        return {'phase': 'running' if self.booted else 'idle'}


class V3BootstrapTests(unittest.TestCase):
    def test_product_bootstrap_owns_one_bounded_runtime_loop(self):
        composition = Composition()
        healthy = []
        bootstrap = ProductBootstrap(
            composition, lambda: {'version': 4}, lambda: None,
            lambda: healthy.append(True),
        )
        result = bootstrap.run(2)
        self.assertEqual(composition.booted, {'version': 4})
        self.assertEqual(result['polls'], 2)
        self.assertEqual(healthy, [True])
        bootstrap.stop()
        self.assertTrue(composition.stopped)

    def test_product_bootstrap_fails_closed_on_invalid_configuration(self):
        bootstrap = ProductBootstrap(Composition(), lambda: None, lambda: None)
        with self.assertRaisesRegex(BootstrapError, 'configuration'):
            bootstrap.start()
        self.assertEqual(bootstrap.snapshot()['state'], 'failed')


if __name__ == '__main__':
    unittest.main()
