"""Opt-in progress push using the existing, trusted device MQTT connection."""
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from binascii import hexlify, unhexlify
from operation_reporting import FIELDS, report_bytes, report_topic, topic_template
from update_security import _hmac_sha256


def validate_reporting(value, device_id, operation_id, configured_broker):
    if not isinstance(value, dict) or set(value) != {'host', 'port', 'topic_template'}:
        raise ValueError('MQTT reporting configuration is invalid')
    host, port = value['host'], value['port']
    if (not isinstance(host, str) or not 1 <= len(host) <= 253 or
            any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-:' for c in host) or
            not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535):
        raise ValueError('MQTT reporting broker is invalid')
    if (not configured_broker.get('trusted_tls') or
            host.lower().rstrip('.') != str(configured_broker.get('host', '')).lower().rstrip('.') or
            port != configured_broker.get('port')):
        raise ValueError('Configure this device to use the selected trusted TLS MQTT broker before MQTT tracking')
    template = topic_template(value['topic_template'])
    report_topic(template, device_id, operation_id)
    return {'host': host.lower().rstrip('.'), 'port': port, 'topic_template': template}


class UpdateOperationReports:
    def __init__(self, operations, broker_getter, connected, publish, now, on_failure=None):
        self.operations = operations
        self.broker_getter = broker_getter
        self.connected = connected
        self.publish = publish
        self.now = now
        self.on_failure = on_failure
        self.sent = {}

    async def tick(self):
        if not self.connected():
            return
        self.operations.open()
        records = self.operations.state['records']
        self.sent = {key: value for key, value in self.sent.items() if any(item['id'] == key for item in records)}
        for record in records:
            if not record.get('report_key') or not record.get('reporting'):
                continue
            try:
                reporting = validate_reporting(record['reporting'], record['device_id'], record['id'], self.broker_getter())
                snapshot = self.operations.snapshot(record['id'])
                marker = (snapshot['revision'], snapshot['percent'], snapshot['boot_epoch'])
                previous = self.sent.get(record['id'], {})
                terminal = record['state'] in ('complete', 'failed', 'cancelled', 'interrupted') or (
                    record['state'] == 'staged' and record['activation'] == 'stage')
                now = self.now()
                if (terminal and marker == previous.get('marker') and previous.get('terminal_since') is not None
                        and now - previous['terminal_since'] > 600):
                    continue
                elapsed = now - previous.get('at', 0)
                if marker == previous.get('marker') and 0 <= elapsed < (30 if terminal else 5):
                    continue
                # Reports contain lifecycle facts, never credential-bearing raw
                # errors, signed policies, command bodies or authentication keys.
                report = {field: snapshot[field] for field in FIELDS}
                report['detail'] = 'Device update ' + report['state']
                self.operations.sample_sequence += 1
                report['sample_sequence'] = self.operations.sample_sequence
                report['mac'] = hexlify(_hmac_sha256(unhexlify(record['report_key']), report_bytes(report))).decode()
                topic = report_topic(reporting['topic_template'], record['device_id'], record['id'])
                if await self.publish({'topic': topic, 'payload': report}, 1, False, False):
                    self.sent[record['id']] = {'marker': marker, 'at': now,
                        'terminal_since': (previous.get('terminal_since', now) if marker == previous.get('marker')
                                           else now) if terminal else None}
            except Exception:
                if self.on_failure:
                    self.on_failure()

    async def run(self):
        while True:
            try:
                await self.tick()
            except Exception:
                if self.on_failure:
                    self.on_failure()
            await asyncio.sleep(2)


def runtime_broker(config, tls_ready):
    return {'host': config['server'], 'port': config['port'],
            'trusted_tls': bool(config['ssl'] and tls_ready)}
