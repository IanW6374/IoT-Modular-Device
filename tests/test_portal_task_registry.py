import asyncio
import unittest

import portal_task_registry


class PortalTaskRegistryTests(unittest.TestCase):
    def test_task_is_reconnectable_and_completes_without_request_state(self):
        tasks = {}
        scheduled = []

        async def operation():
            return 'Finished safely'

        result = portal_task_registry.start(
            tasks, 'release_download', operation(), 'Downloading release',
            lambda name, coroutine: scheduled.append((name, coroutine)),
            lambda *args: None,
        )

        self.assertEqual(result['task_id'], 'release_download')
        self.assertEqual(
            portal_task_registry.status(tasks, 'release_download')['phase'],
            'running',
        )
        asyncio.run(scheduled[0][1])
        current = portal_task_registry.status(tasks, 'release_download')
        self.assertEqual(current['phase'], 'complete')
        self.assertEqual(current['message'], 'Finished safely')
        self.assertEqual(portal_task_registry.snapshot(tasks)[0]['id'], 'release_download')

    def test_progress_is_bounded_and_failure_is_recorded(self):
        tasks = {}
        progress = portal_task_registry.progress(tasks, 'release_download')
        asyncio.run(progress('receiving', 12, 10))
        self.assertEqual(tasks['release_download']['percent'], 100)

        scheduled = []

        async def failing_operation():
            raise RuntimeError('network unavailable')

        portal_task_registry.start(
            tasks, 'certificate-renewal', failing_operation(), 'Renewing',
            lambda name, coroutine: scheduled.append(coroutine),
            lambda *args: None,
        )
        asyncio.run(scheduled[0])
        self.assertEqual(tasks['certificate-renewal']['phase'], 'failed')
        self.assertEqual(tasks['certificate-renewal']['message'], 'network unavailable')

    def test_release_download_can_be_discarded_while_in_progress(self):
        reports = []
        discarded = []
        progress = portal_task_registry.begin_cancellable(
            lambda *values: reports.append(values)
        )

        self.assertEqual(
            portal_task_registry.discard_update(lambda: discarded.append(True)),
            'Update discard requested',
        )
        with self.assertRaisesRegex(ValueError, 'update was discarded'):
            asyncio.run(progress('receiving', 1, 2))
        with self.assertRaisesRegex(ValueError, 'update was discarded'):
            portal_task_registry.finish_cancellable(
                lambda: discarded.append(True)
            )

        self.assertEqual(reports, [])
        self.assertEqual(discarded, [True, True])


if __name__ == '__main__':
    unittest.main()
