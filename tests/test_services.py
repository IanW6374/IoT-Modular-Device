import asyncio
import unittest

from services.messaging_service import MessagingService
from services.network_service import NetworkService, connect_with_retries
from services.portal_service import PortalService
from services.update_service import UpdateService
from services.event_sinks import (
    LegacyLogSink, normalise_legacy_log_level, should_emit_legacy_log,
)
from services.certificate_renewal_service import CertificateRenewalService
from services.mqtt_startup_service import MQTTStartupService


class ServiceBoundaryTests(unittest.TestCase):
    def test_managed_certificate_renewal_records_and_reloads_identity(self):
        outcomes = []
        events = []
        reloads = []

        async def renew(config, paths, progress):
            progress('Renewing identity')
            self.assertEqual(paths['portal-cert'], 'portal.pem')
            return {'portal_not_after': '2030-01-01'}

        class Health:
            def record_event(self, *args, **kwargs):
                events.append((args, kwargs))

        service = CertificateRenewalService(
            {'mode': 'iot_ca'}, {'portal-cert': 'portal.pem'}, renew,
            outcomes.append, Health(), lambda: reloads.append('portal'),
            lambda: reloads.append('identities'), lambda *_args: None, {}
        )
        result = asyncio.run(service.run())
        self.assertIn('2030-01-01', result)
        self.assertEqual(outcomes, [True])
        self.assertEqual(reloads, ['identities'])
        self.assertEqual(events[0][0][0], 'certificate_renewed')

    def test_mqtt_startup_retries_without_latching_device_failure(self):
        started = []
        configured = []

        class Event:
            def clear(self):
                return None

        class Client:
            def __init__(self):
                self.attempts = 0
                self.connected = False
                self.up = Event()

            def isconnected(self):
                return self.connected

            async def connect(self):
                self.attempts += 1
                if self.attempts == 1:
                    raise OSError('broker unavailable')
                self.connected = True

        class State:
            def __init__(self):
                self.values = {}

            def set(self, key, value):
                self.values[key] = value

        async def configure(_client):
            configured.append(True)

        async def worker():
            return None

        async def sleeper(_delay):
            return None

        def start_task(name, coroutine, **_kwargs):
            if name == 'mqtt_startup_retry':
                started.append(coroutine)
            else:
                coroutine.close()

        state = State()
        client = Client()
        service = MQTTStartupService(
            client, configure, worker, (), start_task, state,
            lambda *_args: None, sleeper, str
        )
        self.assertFalse(asyncio.run(service.connect()))
        self.assertEqual(state.values['mqtt'], 'retrying')
        asyncio.run(started[0])
        self.assertEqual(state.values['mqtt'], 'online')
        self.assertEqual(configured, [True])

    def test_legacy_logging_accepts_warning_without_changing_user_levels(self):
        self.assertEqual(normalise_legacy_log_level('warning'), 'WARNING')
        self.assertTrue(should_emit_legacy_log('WARNING', 'INFO'))
        self.assertFalse(should_emit_legacy_log('WARNING', 'ERROR'))
        self.assertEqual(normalise_legacy_log_level('unexpected'), 'INFO')

    def test_structured_event_log_sink_maps_severity(self):
        entries = []
        LegacyLogSink(lambda *args: entries.append(args)).write({
            'component': 'update', 'kind': 'verified',
            'message': 'ready', 'severity': 'warning',
        })
        self.assertEqual(entries[0][0:2], ('Local', 'update verified'))
        self.assertEqual(entries[0][3], 'WARNING')

    def test_network_and_messaging_adapters_copy_external_state(self):
        status = {'connected': True}
        network = NetworkService(lambda: status, lambda: [{'ssid': 'one'}])
        self.assertEqual(network.status(), status)
        self.assertIsNot(network.status(), status)
        sent = []
        messaging = MessagingService(lambda *args: sent.append(args))
        messaging.publish('state/topic', 'on', True, 1)
        self.assertEqual(sent[0], ('state/topic', 'on', True, 1))

    def test_startup_network_retries_before_recovery_escalation(self):
        attempts = []
        delays = []
        retries = []

        async def connector(quick=False):
            attempts.append(quick)
            if len(attempts) < 3:
                raise OSError('temporary Wi-Fi failure')

        async def sleeper(delay):
            delays.append(delay)

        used = asyncio.run(connect_with_retries(
            connector, sleeper, attempts=3, backoff=(2, 5),
            on_retry=lambda completed, total, delay, error: retries.append(
                (completed, total, delay, str(error))
            ),
        ))

        self.assertEqual(used, 3)
        self.assertEqual(attempts, [True, True, True])
        self.assertEqual(delays, [2, 5])
        self.assertEqual(retries, [
            (1, 3, 2, 'temporary Wi-Fi failure'),
            (2, 3, 5, 'temporary Wi-Fi failure'),
        ])

    def test_startup_network_raises_after_bounded_attempts(self):
        async def connector(quick=False):
            raise OSError('offline')

        async def sleeper(_delay):
            return None

        with self.assertRaisesRegex(OSError, 'offline'):
            asyncio.run(connect_with_retries(
                connector, sleeper, attempts=2, backoff=(0,),
            ))

    def test_startup_retry_continues_when_diagnostic_callback_fails(self):
        attempts = []

        async def connector(quick=False):
            attempts.append(quick)
            if len(attempts) == 1:
                raise OSError('temporary Wi-Fi failure')

        async def sleeper(_delay):
            return None

        used = asyncio.run(connect_with_retries(
            connector, sleeper, attempts=3, backoff=(0,),
            on_retry=lambda *unused: (_ for _ in ()).throw(
                ValueError('logger failed')
            ),
        ))
        self.assertEqual(used, 2)
        self.assertEqual(attempts, [True, True])

    def test_update_service_selects_only_declared_receivers(self):
        class Store:
            def begin(self, *args):
                return args
            def status(self, value):
                return {'id': value}
        async def receiver(_reader, _length, _params):
            return 'ready'
        service = UpdateService(
            Store(), {'application': receiver}, lambda: {'ready': False}
        )
        self.assertIs(service.receiver('application'), receiver)
        with self.assertRaisesRegex(ValueError, 'invalid'):
            service.receiver('unknown')

    def test_portal_service_tracks_listener(self):
        async def starter():
            return 'listener'
        service = PortalService(starter)
        import asyncio
        self.assertEqual(asyncio.run(service.start()), 'listener')


if __name__ == '__main__':
    unittest.main()
