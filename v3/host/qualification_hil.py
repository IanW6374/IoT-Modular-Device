#!/usr/bin/env python3
"""Drive guarded on-device qualification scenarios over the mTLS Device API."""

import argparse
import json
import ssl
import time
import urllib.error
import urllib.request
import uuid


class QualificationClient:
    def __init__(self, base_url, ca_file, cert_file, key_file, timeout=10):
        self.base_url = str(base_url).rstrip('/')
        self.timeout = int(timeout)
        self.context = ssl.create_default_context(cafile=ca_file)
        self.context.load_cert_chain(cert_file, key_file)

    def request(self, method, path, value=None):
        body = None if value is None else json.dumps(value).encode()
        request = urllib.request.Request(
            self.base_url + path, data=body, method=method,
            headers={'Content-Type': 'application/json'} if body else {},
        )
        with urllib.request.urlopen(
                request, context=self.context, timeout=self.timeout) as response:
            return json.loads(response.read())

    def get(self, path):
        return self.request('GET', path)

    def post(self, path, value):
        return self.request('POST', path, value)


def _boot(client):
    return client.get('/api/v2/services').get('services', {}).get('boot', {})


def _record(client, gate, outcome, run_id, notes='', evidence_digest=''):
    return client.post('/api/v2/qualification/events', {
        'gate': gate, 'outcome': outcome, 'run_id': run_id,
        'notes': notes, 'evidence_digest': evidence_digest, 'confirm': True,
    })


def watchdog(client, run_id, recovery_timeout):
    before = _boot(client)
    before_count = int(before.get('boot_count', 0) or 0)
    client.post('/api/v2/qualification/scenarios/watchdog-recovery', {
        'run_id': run_id, 'confirmation': 'execute watchdog-recovery',
    })
    deadline = time.monotonic() + int(recovery_timeout)
    last_error = ''
    while time.monotonic() < deadline:
        time.sleep(5)
        try:
            after = _boot(client)
            count = int(after.get('boot_count', 0) or 0)
            cause = str(after.get('reset_cause', '')).lower()
            if count > before_count and ('watchdog' in cause or 'wdt' in cause):
                return _record(
                    client, 'watchdog-recovery', 'success', run_id,
                    'Automated HIL observed boot count advance and watchdog reset cause.'
                )
        except Exception as exc:
            last_error = str(exc)
    try:
        return _record(
            client, 'watchdog-recovery', 'failure', run_id,
            'Device did not return with a watchdog reset cause before timeout: ' +
            last_error[:80]
        )
    except Exception:
        raise RuntimeError(
            'watchdog recovery timed out and the device is unavailable; '
            'record the failure after recovering access'
        )


def native(client, run_id, recovery_timeout, minimum_recovery_s=60,
           clock=time.monotonic, sleeper=time.sleep):
    """Observe a requested frozen-recovery boot and healthy application return."""
    before_boot = _boot(client)
    before_count = int(before_boot.get('boot_count', 0) or 0)
    before_status = client.get('/api/v2/qualification')['qualification']
    before_native = int(
        before_status.get('native_update', {}).get('recovery', {}).get(
            'boot_count', 0
        ) or 0
    )
    release = dict(before_status.get('release', {}))
    client.post('/api/v2/qualification/scenarios/native-recovery', {
        'run_id': run_id, 'confirmation': 'execute native-recovery',
    })
    deadline = clock() + int(recovery_timeout)
    offline_at = None
    last_error = ''
    while clock() < deadline:
        sleeper(5)
        try:
            after_boot = _boot(client)
            device = client.get('/api/v2/device').get('device', {})
            status = client.get('/api/v2/qualification')['qualification']
            native_count = int(
                status.get('native_update', {}).get('recovery', {}).get(
                    'boot_count', 0
                ) or 0
            )
            offline_s = 0 if offline_at is None else int(clock() - offline_at)
            if (
                offline_s >= int(minimum_recovery_s) and
                int(after_boot.get('boot_count', 0) or 0) >= before_count + 2 and
                native_count >= before_native + 2 and
                status.get('release', {}).get('version') == release.get('version') and
                device.get('qualification_observation', {}).get('health_state') == 'healthy'
            ):
                return _record(
                    client, 'native-recovery', 'success', run_id,
                    'HIL observed frozen recovery, two native boots and healthy return.'
                )
        except Exception as exc:
            last_error = str(exc)
            if offline_at is None:
                offline_at = clock()
    try:
        return _record(
            client, 'native-recovery', 'failure', run_id,
            'Native recovery did not complete before timeout: ' + last_error[:96]
        )
    except Exception:
        raise RuntimeError(
            'native recovery timed out and the device is unavailable; '
            'record the failure after recovering access'
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--ca-file', required=True)
    parser.add_argument('--cert-file', required=True)
    parser.add_argument('--key-file', required=True)
    parser.add_argument('--timeout', type=int, default=10)
    sub = parser.add_subparsers(dest='command', required=True)
    watch = sub.add_parser('watchdog')
    watch.add_argument('--run-id', default='')
    watch.add_argument('--recovery-timeout', type=int, default=180)
    native_run = sub.add_parser('native')
    native_run.add_argument('--run-id', default='')
    native_run.add_argument('--recovery-timeout', type=int, default=1200)
    native_run.add_argument('--minimum-recovery-seconds', type=int, default=60)
    scenario = sub.add_parser('scenario')
    scenario.add_argument(
        '--name', choices=('watchdog-recovery', 'native-recovery'), required=True
    )
    scenario.add_argument('--run-id', default='')
    record = sub.add_parser('record')
    record.add_argument('--gate', required=True)
    record.add_argument('--outcome', choices=('success', 'failure'), required=True)
    record.add_argument('--run-id', required=True)
    record.add_argument('--notes', default='')
    record.add_argument('--evidence-digest', default='')
    args = parser.parse_args(argv)
    client = QualificationClient(
        args.url, args.ca_file, args.cert_file, args.key_file, args.timeout
    )
    run_id = getattr(args, 'run_id', '') or (
        'hil-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    )
    if args.command == 'watchdog':
        result = watchdog(client, run_id, args.recovery_timeout)
    elif args.command == 'native':
        result = native(
            client, run_id, args.recovery_timeout,
            args.minimum_recovery_seconds
        )
    elif args.command == 'scenario':
        result = client.post(
            '/api/v2/qualification/scenarios/' + args.name,
            {'run_id': run_id, 'confirmation': 'execute ' + args.name},
        )
    else:
        result = _record(
            client, args.gate, args.outcome, run_id,
            args.notes, args.evidence_digest
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result.get('event', {}).get('outcome') == 'failure' else 0


if __name__ == '__main__':
    raise SystemExit(main())
