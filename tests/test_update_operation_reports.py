import hashlib
import hmac
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from operation_reporting import DEFAULT_TOPIC, FIELDS, report_bytes, report_topic, topic_template
from update_operation_reports import UpdateOperationReports, validate_reporting
from update_operations import UpdateOperations


class OperationReportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ops = UpdateOperations('device', str(Path(self.directory.name) / 'ops'), 'boot')
        self.ops.start_boot()
        self.key = 'a'*64
        self.reporting = {'host': 'mqtt-broker.home.arpa', 'port': 8883, 'topic_template': DEFAULT_TOPIC}
        policy = {'policy_sequence': 1, 'commands': [
            {'id': '%032x' % index, 'action': action, 'release_sequence': 2828, 'release_type': 'universal'}
            for index, action in enumerate(['check-update', 'download-update', 'activate-update'], 1)]}
        self.identifier = self.ops.prepare(policy, self.key, self.reporting)
        self.ops.transition('accepted', detail='secret credential-bearing error is not report data')
        self.broker = {'host': 'mqtt-broker.home.arpa', 'port': 8883, 'trusted_tls': True}
        self.connected = True
        self.clock = 1000.
        self.publish = AsyncMock(return_value=True)
        self.reporter = UpdateOperationReports(self.ops, lambda: self.broker, lambda: self.connected,
                                              self.publish, lambda: self.clock)

    async def test_only_authorized_reports_are_published_and_key_never_leaves_device(self):
        await self.reporter.tick()
        message, qos, logonly, retain = self.publish.call_args.args
        self.assertEqual(message['topic'], report_topic(DEFAULT_TOPIC, 'device', self.identifier))
        value = message['payload']
        self.assertEqual(set(value), set(FIELDS) | {'mac'})
        self.assertEqual(qos, 1)
        self.assertFalse(retain)
        self.assertNotIn(self.key, str(value))
        self.assertNotIn('credential-bearing', str(value))
        self.assertEqual(value['mac'], hmac.new(bytes.fromhex(self.key), report_bytes(value), hashlib.sha256).hexdigest())
        self.assertNotIn('report_key', self.ops.snapshot(self.identifier))
        self.assertNotIn('reporting', self.ops.snapshot(self.identifier))

    async def test_api_only_operation_never_publishes(self):
        self.ops.active().pop('report_key')
        await self.reporter.tick()
        self.publish.assert_not_awaited()

    async def test_broker_or_tls_mismatch_does_not_publish_to_another_destination(self):
        for change in ({'host': 'unapproved.example'}, {'port': 1883}, {'trusted_tls': False}):
            original = dict(self.broker)
            self.broker.update(change)
            await self.reporter.tick()
            self.publish.assert_not_awaited()
            self.broker = original

    async def test_disconnected_broker_does_not_touch_installer_or_progress(self):
        generation = self.ops.state['generation']
        self.connected = False
        await self.reporter.tick()
        self.publish.assert_not_awaited()
        self.assertEqual(self.ops.state['generation'], generation)

    async def test_progress_coalesces_and_heartbeat_does_not_write_flash(self):
        await self.reporter.tick()
        generation = self.ops.state['generation']
        await self.reporter.tick()
        self.assertEqual(self.publish.await_count, 1)
        self.clock += 5
        await self.reporter.tick()
        self.assertEqual(self.publish.await_count, 2)
        self.assertEqual(self.ops.state['generation'], generation)
        self.ops.transition('checking', 'inspect')
        self.ops.progress('core_write', 10, ['queued', 'inspect'])
        await self.reporter.tick()
        value = self.publish.call_args.args[0]['payload']
        self.assertEqual(value['percent'], 10)

    async def test_custom_topic_recommended_defaults_and_clock_wrap(self):
        self.ops.active()['reporting']['topic_template'] = 'custom/{device_id}/progress/{operation_id}'
        await self.reporter.tick()
        self.assertTrue(self.publish.call_args.args[0]['topic'].startswith('custom/device/progress/'))
        self.clock = 1  # ticks_ms wrap: unchanged progress must still heartbeat.
        await self.reporter.tick()
        self.assertEqual(self.publish.await_count, 2)

    async def test_terminal_reports_stop_repeating_but_new_terminal_revision_is_sent(self):
        self.ops.transition('failed')
        await self.reporter.tick()
        self.clock += 601
        await self.reporter.tick()
        self.assertEqual(self.publish.await_count, 1)

    def test_topic_requires_unique_identity_levels_and_rejects_wildcards(self):
        for template in ('iotmd/#', 'iotmd/{device_id}', '/{device_id}/{operation_id}',
                         'a/{device_id}/{operation_id}/+', 'a/{device_id}{operation_id}',
                         'a/{device_id}/{device_id}/{operation_id}', 'a/{device_id}/{operation_id}/{other}'):
            with self.assertRaises(ValueError): topic_template(template)
        with self.assertRaises(ValueError): report_topic(DEFAULT_TOPIC, 'device/#', 'a'*32)
        long_template = 'x'*165 + '/{device_id}/{operation_id}'
        with self.assertRaises(ValueError): report_topic(long_template, 'd'*64, 'a'*32)

    def test_reporting_validation_does_not_accept_missing_broker_security(self):
        self.assertEqual(validate_reporting(self.reporting, 'device', self.identifier, self.broker), self.reporting)
        with self.assertRaises(ValueError): validate_reporting({}, 'device', self.identifier, self.broker)
