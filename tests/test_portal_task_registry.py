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


if __name__ == '__main__':
    unittest.main()
