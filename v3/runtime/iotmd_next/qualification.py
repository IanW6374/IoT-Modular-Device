"""Persistent, bounded evidence for v3 operational qualification gates."""

try:
    import ujson as json
except ImportError:
    import json

from .storage import StorageContractError


CONTRACT_VERSION = 1
STATE_VERSION = 3
CAMPAIGN_STATE_VERSION = 1
MAX_COUNTER = 1000000
MAX_RELEASE_HISTORY = 4
MAX_RETRY_HISTORY = 8
MAX_HISTORY_BYTES = 4096
GATE_NAMES = (
    'soak', 'health', 'storage', 'network-recovery', 'certificate-renewal',
    'paired-updates', 'power-recovery', 'canary-health',
    'release-confirmation', 'native-recovery', 'watchdog-recovery',
    'identity-interoperability', 'fleet-interoperability',
    'migration-rollback', 'driver-hardware',
)

VALIDATION_COUNTERS = {
    'native-recovery': 'native_recoveries',
    'watchdog-recovery': 'watchdog_recoveries',
    'identity-interoperability': 'identity_transactions',
    'fleet-interoperability': 'fleet_transactions',
    'migration-rollback': 'migration_rollbacks',
    'driver-hardware': 'driver_checks',
}

CAMPAIGN_COUNTERS = (
    'renewal_attempts', 'renewal_successes', 'renewal_failures',
    'update_trials', 'update_confirmations', 'update_failures',
    'update_rollbacks', 'power_interruptions', 'power_recoveries',
    'power_failures', 'native_recoveries_attempts',
    'native_recoveries_successes', 'native_recoveries_failures',
    'watchdog_recoveries_attempts', 'watchdog_recoveries_successes',
    'watchdog_recoveries_failures', 'identity_transactions_attempts',
    'identity_transactions_successes', 'identity_transactions_failures',
    'fleet_transactions_attempts', 'fleet_transactions_successes',
    'fleet_transactions_failures', 'migration_rollbacks_attempts',
    'migration_rollbacks_successes', 'migration_rollbacks_failures',
    'driver_checks_attempts', 'driver_checks_successes',
    'driver_checks_failures',
)


class QualificationError(RuntimeError):
    pass


def _integer(value, name, minimum=0, maximum=2147483647):
    if (not isinstance(value, int) or isinstance(value, bool) or
            value < minimum or value > maximum):
        raise QualificationError(name + ' is invalid')
    return value


def _text(value, name, maximum=64):
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise QualificationError(name + ' is invalid')
    return value


def validate_profile(value):
    required = {
        'name', 'minimum_soak_s', 'maximum_consecutive_unhealthy',
        'minimum_health_samples', 'minimum_storage_samples',
        'minimum_storage_free_bytes', 'maximum_network_recovery_s',
        'required_network_recoveries', 'required_renewals',
        'required_update_confirmations', 'required_power_recoveries',
        'required_native_recoveries', 'required_watchdog_recoveries',
        'required_identity_transactions', 'required_fleet_transactions',
        'required_migration_rollbacks', 'required_driver_checks',
    }
    if not isinstance(value, dict) or set(value) != required:
        raise QualificationError('qualification profile has invalid fields')
    result = dict(value)
    _text(result['name'], 'qualification profile name', 32)
    _integer(result['minimum_soak_s'], 'minimum soak', 60, 604800)
    _integer(
        result['maximum_consecutive_unhealthy'],
        'maximum consecutive unhealthy samples', 0, 1000
    )
    _integer(result['minimum_health_samples'], 'minimum health samples', 1, 1000000)
    _integer(
        result['minimum_storage_samples'], 'minimum storage samples', 1, 1000000
    )
    _integer(
        result['minimum_storage_free_bytes'], 'minimum storage free bytes',
        0, 1073741824
    )
    _integer(
        result['maximum_network_recovery_s'], 'maximum network recovery',
        1, 86400
    )
    for key in (
        'required_network_recoveries', 'required_renewals',
        'required_update_confirmations', 'required_power_recoveries',
        'required_native_recoveries', 'required_watchdog_recoveries',
        'required_identity_transactions', 'required_fleet_transactions',
        'required_migration_rollbacks', 'required_driver_checks',
    ):
        _integer(result[key], key.replace('_', ' '), 1, 1000)
    return result


def beta_profile():
    """Return the minimum evidence profile for a v3 beta candidate."""
    return {
        'name': 'v3-beta',
        'minimum_soak_s': 172800,
        'maximum_consecutive_unhealthy': 3,
        'minimum_health_samples': 2400,
        'minimum_storage_samples': 2400,
        'minimum_storage_free_bytes': 131072,
        'maximum_network_recovery_s': 300,
        'required_network_recoveries': 3,
        'required_renewals': 1,
        'required_update_confirmations': 3,
        'required_power_recoveries': 3,
        'required_native_recoveries': 3,
        'required_watchdog_recoveries': 3,
        'required_identity_transactions': 1,
        'required_fleet_transactions': 1,
        'required_migration_rollbacks': 1,
        'required_driver_checks': 13,
    }


def _counters():
    return {
        'samples': 0,
        'health_samples': 0,
        'storage_samples': 0,
        'unhealthy_samples': 0,
        'consecutive_unhealthy': 0,
        'maximum_consecutive_unhealthy': 0,
        'network_interruptions': 0,
        'network_recoveries': 0,
        'renewal_attempts': 0,
        'renewal_successes': 0,
        'renewal_failures': 0,
        'update_trials': 0,
        'update_confirmations': 0,
        'update_failures': 0,
        'update_rollbacks': 0,
        'power_interruptions': 0,
        'power_recoveries': 0,
        'power_failures': 0,
        'native_recoveries_attempts': 0,
        'native_recoveries_successes': 0,
        'native_recoveries_failures': 0,
        'watchdog_recoveries_attempts': 0,
        'watchdog_recoveries_successes': 0,
        'watchdog_recoveries_failures': 0,
        'identity_transactions_attempts': 0,
        'identity_transactions_successes': 0,
        'identity_transactions_failures': 0,
        'fleet_transactions_attempts': 0,
        'fleet_transactions_successes': 0,
        'fleet_transactions_failures': 0,
        'migration_rollbacks_attempts': 0,
        'migration_rollbacks_successes': 0,
        'migration_rollbacks_failures': 0,
        'driver_checks_attempts': 0,
        'driver_checks_successes': 0,
        'driver_checks_failures': 0,
    }


def _empty_state(started_at, release_version='', release_sequence=0):
    return {
        'state_version': STATE_VERSION,
        'release_version': release_version,
        'release_sequence': release_sequence,
        'started_at': started_at,
        'last_sample_at': started_at,
        'minimum_storage_free_bytes': None,
        'maximum_network_recovery_s': 0,
        'network_up': None,
        'network_outage_started_at': 0,
        'canary_paused': False,
        'gate_started_at': {'health': started_at, 'storage': started_at},
        'counters': _counters(),
    }


def _empty_campaign(campaign_id, started_at):
    return {
        'state_version': CAMPAIGN_STATE_VERSION,
        'campaign_id': campaign_id,
        'started_at': started_at,
        'counters': {key: 0 for key in CAMPAIGN_COUNTERS},
    }


def _bounded_increment(value):
    return min(MAX_COUNTER, int(value) + 1)


def _validate_history(value):
    if not isinstance(value, list) or len(value) > MAX_RELEASE_HISTORY:
        raise QualificationError('qualification history is invalid')
    required = {
        'release_version', 'release_sequence', 'observed_at',
        'promotion_ready', 'passed_gates', 'failed_gates',
    }
    for item in value:
        if not isinstance(item, dict) or set(item) != required:
            raise QualificationError('qualification history entry is invalid')
        _text(item['release_version'], 'qualification history release', 48)
        _integer(
            item['release_sequence'], 'qualification history release sequence'
        )
        _integer(item['observed_at'], 'qualification history observation', 1)
        if item['promotion_ready'] not in (True, False):
            raise QualificationError('qualification history result is invalid')
        for key in ('passed_gates', 'failed_gates'):
            gates = item[key]
            if (not isinstance(gates, list) or len(gates) > len(GATE_NAMES) or
                    len(set(gates)) != len(gates) or
                    any(name not in GATE_NAMES for name in gates)):
                raise QualificationError('qualification history gates are invalid')


def _empty_history():
    return {'history_version': 2, 'current': None, 'releases': [],
            'retries': [], 'retry_generation': 0}


def _decode_history(payload):
    if not payload:
        return _empty_history()
    try:
        value = json.loads(payload.decode())
    except Exception:
        raise QualificationError('qualification history is invalid')
    if isinstance(value, dict) and value.get('history_version') == 1:
        value.update(history_version=2, retries=[], retry_generation=0)
    if (not isinstance(value, dict) or set(value) != set(_empty_history()) or
            value['history_version'] != 2):
        raise QualificationError('qualification history has invalid fields')
    _integer(value['retry_generation'], 'qualification retry generation')
    if not isinstance(value['retries'], list) or len(value['retries']) > MAX_RETRY_HISTORY:
        raise QualificationError('qualification retry history is invalid')
    for retry in value['retries']:
        if not isinstance(retry, dict) or set(retry) != {
                'gate', 'time', 'actor', 'reason', 'release_version',
                'release_sequence', 'observed', 'required', 'detail'}:
            raise QualificationError('qualification retry record is invalid')
        if retry['gate'] not in GATE_NAMES:
            raise QualificationError('qualification retry gate is invalid')
        for field in ('time', 'release_sequence', 'observed', 'required'):
            _integer(retry[field], 'qualification retry ' + field)
        for field, limit in (('actor', 64), ('reason', 160),
                             ('release_version', 48), ('detail', 512)):
            _text(retry[field], 'qualification retry ' + field, limit)
    _validate_history(value['releases'])
    if value['current'] is not None:
        _validate_history([value['current']])
    return value


def _decode(payload):
    if not payload:
        return None
    try:
        value = json.loads(payload.decode())
    except Exception:
        raise QualificationError('qualification state is invalid')
    template = _empty_state(1)
    if isinstance(value, dict) and value.get('state_version') == 2:
        value['state_version'] = STATE_VERSION
        value['gate_started_at'] = {
            'health': value.get('started_at'), 'storage': value.get('started_at')
        }
    if not isinstance(value, dict) or set(value) != set(template):
        raise QualificationError('qualification state has invalid fields')
    if value['state_version'] != STATE_VERSION:
        raise QualificationError('qualification state version is unsupported')
    _text(value['release_version'], 'qualification state release', 48)
    _integer(value['release_sequence'], 'qualification state release sequence')
    for key in ('started_at', 'last_sample_at', 'maximum_network_recovery_s',
                'network_outage_started_at'):
        _integer(value[key], 'qualification ' + key.replace('_', ' '))
    minimum_free = value['minimum_storage_free_bytes']
    if minimum_free is not None:
        _integer(minimum_free, 'qualification minimum storage free bytes')
    if value['network_up'] not in (None, True, False):
        raise QualificationError('qualification network state is invalid')
    if value['canary_paused'] not in (True, False):
        raise QualificationError('qualification canary state is invalid')
    starts = value['gate_started_at']
    if not isinstance(starts, dict) or set(starts) != {'health', 'storage'}:
        raise QualificationError('qualification gate start times are invalid')
    for started in starts.values():
        _integer(started, 'qualification gate start')
    counters = value['counters']
    if not isinstance(counters, dict) or set(counters) != set(_counters()):
        raise QualificationError('qualification counters are invalid')
    for key in counters:
        _integer(counters[key], 'qualification counter ' + key, 0, MAX_COUNTER)
    return value


def _decode_campaign(payload):
    if not payload:
        return None
    try:
        value = json.loads(payload.decode())
    except Exception:
        raise QualificationError('qualification campaign state is invalid')
    template = _empty_campaign('campaign', 1)
    if not isinstance(value, dict) or set(value) != set(template):
        raise QualificationError('qualification campaign has invalid fields')
    if value['state_version'] != CAMPAIGN_STATE_VERSION:
        raise QualificationError('qualification campaign version is unsupported')
    _text(value['campaign_id'], 'qualification campaign id', 48)
    _integer(value['started_at'], 'qualification campaign start', 1)
    counters = value['counters']
    if not isinstance(counters, dict) or set(counters) != set(CAMPAIGN_COUNTERS):
        raise QualificationError('qualification campaign counters are invalid')
    for key in counters:
        _integer(counters[key], 'qualification campaign counter ' + key,
                 0, MAX_COUNTER)
    return value


class OperationalQualification:
    """Record only observed evidence; never infer an unexecuted test passed."""

    def __init__(self, namespace, now, device_id, release_getter, profile=None,
                 history_namespace=None, campaign_namespace=None,
                 campaign_id='v3-platform-abi-6'):
        if not callable(now) or not callable(release_getter):
            raise QualificationError('qualification providers are unavailable')
        self._namespace = namespace
        self._now = now
        self._device_id = _text(str(device_id), 'qualification device id')
        self._release_getter = release_getter
        self._profile = validate_profile(profile or beta_profile())
        self._state = None
        self._history_namespace = history_namespace
        self._history = _empty_history()
        self._campaign_namespace = campaign_namespace
        self._campaign_id = _text(
            str(campaign_id), 'qualification campaign id', 48
        )
        self._campaign = None

    def _save(self):
        generation, unused = self._namespace.snapshot()
        try:
            payload = json.dumps(
                self._state, sort_keys=True, separators=(',', ':')
            ).encode()
        except TypeError:
            payload = json.dumps(self._state).encode()
        self._namespace.commit(generation, payload)

    def _save_history(self):
        if self._history_namespace is None:
            return
        generation, unused = self._history_namespace.snapshot()
        while True:
            try:
                payload = json.dumps(
                    self._history, sort_keys=True, separators=(',', ':')
                ).encode()
            except TypeError:
                payload = json.dumps(self._history).encode()
            if len(payload) <= MAX_HISTORY_BYTES:
                break
            if self._history['releases']:
                self._history['releases'] = self._history['releases'][1:]
            elif len(self._history['retries']) > 1:
                self._history['retries'] = self._history['retries'][1:]
            else:
                raise QualificationError('qualification retry history exceeds storage capacity')
        self._history_namespace.commit(generation, payload)

    def _save_history_resilient(self):
        """Persist derived history without making live qualification unavailable."""
        while True:
            try:
                self._save_history()
                return True
            except StorageContractError as exc:
                if str(exc) != 'encrypted transactional storage is full':
                    raise
                releases = self._history['releases']
                if not releases:
                    return False
                # Earlier summaries are diagnostic convenience. Prefer a
                # smaller, current record over failing the live recorder when
                # the bounded NVS partition is under pressure.
                self._history['releases'] = releases[1:]

    def _save_campaign(self):
        if self._campaign_namespace is None:
            return
        generation, unused = self._campaign_namespace.snapshot()
        try:
            payload = json.dumps(
                self._campaign, sort_keys=True, separators=(',', ':')
            ).encode()
        except TypeError:
            payload = json.dumps(self._campaign).encode()
        self._campaign_namespace.commit(generation, payload)

    def _load_campaign(self, now):
        if self._campaign_namespace is None:
            self._campaign = None
            return
        unused, payload = self._campaign_namespace.snapshot()
        campaign = _decode_campaign(payload)
        if campaign is None or campaign['campaign_id'] != self._campaign_id:
            campaign = _empty_campaign(self._campaign_id, now)
            # Adopt evidence recorded before campaign-scoped persistence was
            # introduced. This is a one-time migration, not manufactured data.
            if self._state is not None:
                for key in CAMPAIGN_COUNTERS:
                    campaign['counters'][key] = self._state['counters'][key]
            self._campaign = campaign
            self._save_campaign()
        else:
            self._campaign = campaign

    def _load_history(self):
        if self._history_namespace is None:
            self._history = _empty_history()
            return
        unused, payload = self._history_namespace.snapshot()
        self._history = _decode_history(payload)

    @staticmethod
    def _summary(evidence):
        return {
            'release_version': evidence['release']['version'],
            'release_sequence': evidence['release']['sequence'],
            'observed_at': evidence['observed_at'],
            'promotion_ready': evidence['promotion_ready'],
            'passed_gates': [
                gate['name'] for gate in evidence['gates']
                if gate['status'] == 'passed'
            ],
            'failed_gates': [
                gate['name'] for gate in evidence['gates']
                if gate['status'] == 'failed'
            ],
        }

    def _sync_history(self, evidence):
        if self._history_namespace is None:
            return
        summary = self._summary(evidence)
        current = self._history['current']
        comparable = dict(summary)
        comparable.pop('observed_at')
        previous = dict(current or {})
        previous.pop('observed_at', None)
        if comparable != previous:
            self._history['current'] = summary
            if not self._save_history_resilient():
                # Keep reads deterministic and retry the derived sidecar on a
                # later evidence mutation. The authoritative counters have
                # already been committed separately.
                self._history['current'] = current

    def _release(self):
        release = self._release_getter()
        if not isinstance(release, dict):
            raise QualificationError('qualification release is invalid')
        return {
            'version': _text(
                str(release.get('version', '')), 'qualification release', 48
            ),
            'sequence': _integer(
                int(release.get('sequence', 0)),
                'qualification release sequence'
            ),
            'confirmed': bool(release.get('confirmed', False)),
        }

    def start(self):
        now = _integer(int(self._now()), 'qualification time', 1)
        release = self._release()
        unused, payload = self._namespace.snapshot()
        self._load_history()
        self._state = _decode(payload) or _empty_state(
            now, release['version'], release['sequence']
        )
        self._load_campaign(now)
        changed_release = (
            self._state['release_version'] != release['version'] or
            self._state['release_sequence'] != release['sequence']
        )
        if changed_release:
            current = self._history['current']
            if current is None:
                current = self._summary(self._snapshot_for_release({
                    'version': self._state['release_version'],
                    'sequence': self._state['release_sequence'],
                    # Pre-history state did not retain this observation. Do
                    # not manufacture a passed confirmation gate.
                    'confirmed': False,
                }, now))
            if current is not None and (
                    current['release_version'] == self._state['release_version'] and
                    current['release_sequence'] == self._state['release_sequence']):
                releases = list(self._history['releases'])
                releases.append(current)
                self._history['releases'] = releases[-MAX_RELEASE_HISTORY:]
                self._history['current'] = None
                self._save_history_resilient()
            self._state = _empty_state(
                now, release['version'], release['sequence']
            )
        if not payload or changed_release:
            self._save()
        return self.snapshot()

    def close(self):
        """Release every native namespace owned by this recorder."""
        closed = []
        for namespace in (
                self._campaign_namespace, self._history_namespace,
                self._namespace):
            if namespace is None or any(
                    namespace is item for item in closed):
                continue
            closer = getattr(namespace, 'close', None)
            if callable(closer):
                try:
                    closer()
                except Exception:
                    pass
            closed.append(namespace)
        self._state = None
        self._campaign = None
        self._history = _empty_history()
        return len(closed)

    def reset(self):
        """Explicitly reset release observations and the active ABI campaign."""
        release = self._release()
        self._state = _empty_state(
            _integer(int(self._now()), 'qualification time', 1),
            release['version'], release['sequence']
        )
        self._save()
        if self._campaign_namespace is not None:
            self._campaign = _empty_campaign(
                self._campaign_id,
                _integer(int(self._now()), 'qualification time', 1)
            )
            self._save_campaign()
        return self.snapshot()

    def reset_campaign(self):
        """Explicitly clear cross-release evidence for the active ABI campaign."""
        return self.reset()

    def history(self):
        """Return bounded summaries for earlier releases on this device."""
        self._require_started()
        return [dict(item) for item in self._history['releases']]

    def retry_history(self):
        self._require_started()
        return [dict(item) for item in self._history['retries']]

    def retry_generation(self):
        self._require_started()
        return self._history['retry_generation']

    def restart_failed_gate(self, name, actor, reason, generation):
        """Archive failed evidence before clearing only its active test window."""
        self._require_started()
        if self._history_namespace is None:
            raise QualificationError('persistent retry history is unavailable')
        if _integer(generation, 'retry generation') != self.retry_generation():
            raise QualificationError('qualification changed; refresh before retrying')
        actor = _text(actor, 'administrator', 64)
        reason = _text(reason.strip(), 'retry reason', 160)
        evidence = self.snapshot()
        gate = next((item for item in evidence['gates'] if item['name'] == name), None)
        if gate is None or gate['status'] != 'failed':
            raise QualificationError('only a failed qualification gate can be restarted')
        if name == 'canary-health':
            raise QualificationError('resolve the active canary pause; this gate clears automatically')
        if name == 'paired-updates' and self._campaign is None:
            raise QualificationError('persistent campaign is required to preserve canary evidence')
        keys = {
            'health': ('health_samples', 'unhealthy_samples',
                       'consecutive_unhealthy', 'maximum_consecutive_unhealthy'),
            'storage': ('storage_samples',),
            'network-recovery': ('network_interruptions', 'network_recoveries'),
            'certificate-renewal': ('renewal_attempts', 'renewal_successes', 'renewal_failures'),
            'paired-updates': ('update_trials', 'update_confirmations',
                              'update_failures', 'update_rollbacks'),
            'power-recovery': ('power_interruptions', 'power_recoveries', 'power_failures'),
        }.get(name)
        if name in VALIDATION_COUNTERS:
            keys = tuple(VALIDATION_COUNTERS[name] + suffix for suffix in
                         ('_attempts', '_successes', '_failures'))
        if not keys:
            raise QualificationError('this qualification gate cannot be restarted')
        now = _integer(int(self._now()), 'qualification time', 1)
        archived = dict(self._history)
        archived['retries'] = (list(archived['retries']) + [{
            'gate': name, 'time': now, 'actor': actor, 'reason': reason,
            'release_version': evidence['release']['version'],
            'release_sequence': evidence['release']['sequence'],
            'observed': gate['observed'], 'required': gate['required'],
            'detail': json.dumps({
                'counters': {key: evidence['counters'][key] for key in keys},
                'measurements': evidence['measurements'],
            }),
        }])[-MAX_RETRY_HISTORY:]
        _text(archived['retries'][-1]['detail'], 'archived failure detail', 512)
        archived['retry_generation'] += 1
        previous_history = self._history
        self._history = archived
        try:
            self._save_history()  # Fail closed: no reset without durable evidence.
        except Exception:
            self._history = previous_history
            raise
        campaign = self._campaign is not None and all(key in CAMPAIGN_COUNTERS for key in keys)
        previous = self._campaign if campaign else self._state
        updated = dict(previous)
        updated['counters'] = dict(previous['counters'])
        for key in keys:
            updated['counters'][key] = 0
        if not campaign:
            updated['gate_started_at'] = dict(previous['gate_started_at'])
            if name in ('health', 'storage'):
                updated['gate_started_at'][name] = now
            if name == 'storage':
                updated['minimum_storage_free_bytes'] = None
            elif name == 'network-recovery':
                updated.update(maximum_network_recovery_s=0, network_up=None,
                               network_outage_started_at=0)
        try:
            if campaign:
                self._campaign = updated
                self._save_campaign()
            else:
                self._state = updated
                self._save()
        except Exception:
            if campaign:
                self._campaign = previous
            else:
                self._state = previous
            raise
        return self.snapshot()

    def _require_started(self):
        if self._state is None:
            raise QualificationError('qualification recorder is not started')

    def sample(self, health_state, storage_free_bytes, network_up,
               canary_paused=False):
        self._require_started()
        if health_state not in (None, 'healthy', 'degraded', 'failed'):
            raise QualificationError('qualification health state is invalid')
        free = None
        if storage_free_bytes is not None:
            free = _integer(
                storage_free_bytes, 'qualification storage free bytes', 0,
                1073741824
            )
        if network_up not in (True, False) or canary_paused not in (True, False):
            raise QualificationError('qualification sample flags are invalid')
        now = _integer(int(self._now()), 'qualification time', 1)
        if now < self._state['last_sample_at']:
            raise QualificationError('qualification time moved backwards')
        counters = self._state['counters']
        counters['samples'] = _bounded_increment(counters['samples'])
        if health_state is not None:
            counters['health_samples'] = _bounded_increment(
                counters['health_samples']
            )
            if health_state == 'healthy':
                counters['consecutive_unhealthy'] = 0
            else:
                counters['unhealthy_samples'] = _bounded_increment(
                    counters['unhealthy_samples']
                )
                counters['consecutive_unhealthy'] = _bounded_increment(
                    counters['consecutive_unhealthy']
                )
                counters['maximum_consecutive_unhealthy'] = max(
                    counters['maximum_consecutive_unhealthy'],
                    counters['consecutive_unhealthy']
                )
        if free is not None:
            counters['storage_samples'] = _bounded_increment(
                counters['storage_samples']
            )
            minimum_free = self._state['minimum_storage_free_bytes']
            self._state['minimum_storage_free_bytes'] = (
                free if minimum_free is None else min(minimum_free, free)
            )
        previous_network = self._state['network_up']
        if previous_network is True and not network_up:
            counters['network_interruptions'] = _bounded_increment(
                counters['network_interruptions']
            )
            self._state['network_outage_started_at'] = now
        elif previous_network is False and network_up:
            counters['network_recoveries'] = _bounded_increment(
                counters['network_recoveries']
            )
            started = self._state['network_outage_started_at']
            recovery = max(0, now - started) if started else 0
            self._state['maximum_network_recovery_s'] = max(
                self._state['maximum_network_recovery_s'], recovery
            )
            self._state['network_outage_started_at'] = 0
        self._state['network_up'] = network_up
        self._state['canary_paused'] = canary_paused
        self._state['last_sample_at'] = now
        self._save()
        result = self.snapshot()
        self._sync_history(result)
        return result

    def record_renewal(self, successful):
        self._record_boolean('renewal', successful)

    def record_update(self, outcome):
        self._require_started()
        if outcome not in ('confirmed', 'failed', 'rolled-back'):
            raise QualificationError('qualification update outcome is invalid')
        counters = self._state['counters']
        counters['update_trials'] = _bounded_increment(counters['update_trials'])
        key = {
            'confirmed': 'update_confirmations',
            'failed': 'update_failures',
            'rolled-back': 'update_rollbacks',
        }[outcome]
        counters[key] = _bounded_increment(counters[key])
        self._save()
        self._record_campaign(('update_trials', key))
        self._sync_history(self.snapshot())

    def record_power_recovery(self, successful):
        self._record_boolean('power', successful)

    def record_validation(self, name, successful):
        self._require_started()
        if name not in VALIDATION_COUNTERS or successful not in (True, False):
            raise QualificationError('qualification validation is invalid')
        prefix = VALIDATION_COUNTERS[name]
        counters = self._state['counters']
        counters[prefix + '_attempts'] = _bounded_increment(
            counters[prefix + '_attempts']
        )
        outcome = prefix + ('_successes' if successful else '_failures')
        counters[outcome] = _bounded_increment(counters[outcome])
        self._save()
        self._record_campaign((prefix + '_attempts', outcome))
        self._sync_history(self.snapshot())

    def _record_boolean(self, kind, successful):
        self._require_started()
        if successful not in (True, False):
            raise QualificationError('qualification outcome is invalid')
        counters = self._state['counters']
        attempt_key = kind + ('_attempts' if kind == 'renewal' else '_interruptions')
        success_key = kind + ('_successes' if kind == 'renewal' else '_recoveries')
        failure_key = kind + '_failures'
        counters[attempt_key] = _bounded_increment(counters[attempt_key])
        counters[success_key if successful else failure_key] = _bounded_increment(
            counters[success_key if successful else failure_key]
        )
        self._save()
        self._record_campaign((
            attempt_key, success_key if successful else failure_key
        ))
        self._sync_history(self.snapshot())

    def _record_campaign(self, keys):
        if self._campaign is None:
            return
        counters = self._campaign['counters']
        for key in keys:
            counters[key] = _bounded_increment(counters[key])
        self._save_campaign()

    def _evidence_counters(self):
        counters = dict(self._state['counters'])
        if self._campaign is not None:
            for key in CAMPAIGN_COUNTERS:
                counters[key] = self._campaign['counters'][key]
        return counters

    def _gate(self, name, status, observed, required):
        return {
            'name': name, 'status': status,
            'observed': int(observed), 'required': int(required),
        }

    def snapshot(self):
        self._require_started()
        release = self._release()
        if (
            self._state['release_version'] != release['version'] or
            self._state['release_sequence'] != release['sequence']
        ):
            raise QualificationError(
                'qualification release changed; restart recorder'
            )
        return self._snapshot_for_release(release)

    def _snapshot_for_release(self, release, observed_at=None):
        """Evaluate the loaded state against an explicitly bound release."""
        now = max(
            self._state['last_sample_at'],
            (_integer(int(self._now()), 'qualification time', 1)
             if observed_at is None else
             _integer(int(observed_at), 'qualification time', 1))
        )
        elapsed = max(0, now - self._state['started_at'])
        profile = self._profile
        release_counters = self._state['counters']
        counters = self._evidence_counters()
        soak_passed = elapsed >= profile['minimum_soak_s']
        gates = [self._gate(
            'soak', 'passed' if soak_passed else 'in-progress', elapsed,
            profile['minimum_soak_s']
        )]
        unhealthy = counters['maximum_consecutive_unhealthy']
        health_samples = counters['health_samples']
        health_status = (
            'failed' if unhealthy > profile['maximum_consecutive_unhealthy']
            else ('not-run' if not health_samples else
                  ('passed' if (
                      now - self._state['gate_started_at']['health'] >= profile['minimum_soak_s'] and
                      health_samples >= profile['minimum_health_samples']
                  ) else 'in-progress'))
        )
        gates.append(self._gate(
            'health', health_status, health_samples,
            profile['minimum_health_samples']
        ))
        minimum_free = self._state['minimum_storage_free_bytes']
        storage_samples = counters['storage_samples']
        if minimum_free is None:
            storage_status = 'not-run'
        else:
            storage_status = (
                'failed' if minimum_free < profile['minimum_storage_free_bytes']
                else ('passed' if (
                    now - self._state['gate_started_at']['storage'] >= profile['minimum_soak_s'] and
                    storage_samples >= profile['minimum_storage_samples']
                ) else 'in-progress')
            )
        gates.append(self._gate(
            'storage', storage_status, storage_samples,
            profile['minimum_storage_samples']
        ))
        recoveries = counters['network_recoveries']
        active_outage = (
            max(0, now - self._state['network_outage_started_at'])
            if self._state['network_up'] is False and
            self._state['network_outage_started_at'] else 0
        )
        maximum_recovery = max(
            self._state['maximum_network_recovery_s'], active_outage
        )
        network_status = (
            'failed' if (
                maximum_recovery >
                profile['maximum_network_recovery_s']
            ) else ('passed' if recoveries >= profile['required_network_recoveries']
                    else ('not-run' if not counters['network_interruptions']
                          else 'in-progress'))
        )
        gates.append(self._gate(
            'network-recovery', network_status, recoveries,
            profile['required_network_recoveries']
        ))
        for name, counter, failure_counters, requirement in (
            ('certificate-renewal', 'renewal_successes',
             ('renewal_failures',), 'required_renewals'),
            ('paired-updates', 'update_confirmations',
             ('update_failures',),
             'required_update_confirmations'),
            ('power-recovery', 'power_recoveries',
             ('power_failures',), 'required_power_recoveries'),
        ):
            observed = counters[counter]
            attempts = {
                'certificate-renewal': counters['renewal_attempts'],
                'paired-updates': counters['update_trials'],
                'power-recovery': counters['power_interruptions'],
            }[name]
            status = (
                'failed' if any(counters[key] for key in failure_counters)
                else ('passed' if observed >= profile[requirement]
                else ('not-run' if attempts == 0 else 'in-progress')
                )
            )
            gates.append(self._gate(name, status, observed, profile[requirement]))
        release_confirmed = release['confirmed']
        canary_status = (
            'failed' if self._state['canary_paused'] else
            ('passed' if release_counters['update_confirmations'] else 'not-run')
        )
        gates.append(self._gate(
            'canary-health', canary_status,
            (0 if self._state['canary_paused'] else
             release_counters['update_confirmations']),
            1
        ))
        gates.append(self._gate(
            'release-confirmation',
            'passed' if release_confirmed else 'in-progress',
            1 if release_confirmed else 0, 1
        ))
        validation_requirements = {
            'native-recovery': 'required_native_recoveries',
            'watchdog-recovery': 'required_watchdog_recoveries',
            'identity-interoperability': 'required_identity_transactions',
            'fleet-interoperability': 'required_fleet_transactions',
            'migration-rollback': 'required_migration_rollbacks',
            'driver-hardware': 'required_driver_checks',
        }
        for name in (
            'native-recovery', 'watchdog-recovery',
            'identity-interoperability', 'fleet-interoperability',
            'migration-rollback', 'driver-hardware',
        ):
            prefix = VALIDATION_COUNTERS[name]
            attempts = counters[prefix + '_attempts']
            successes = counters[prefix + '_successes']
            failures = counters[prefix + '_failures']
            required = profile[validation_requirements[name]]
            status = (
                'failed' if failures else
                ('passed' if successes >= required else
                 ('not-run' if not attempts else 'in-progress'))
            )
            gates.append(self._gate(name, status, successes, required))
        result = {
            'contract_version': CONTRACT_VERSION,
            'profile': profile['name'],
            'device_id': self._device_id,
            'release': {
                'version': release['version'],
                'sequence': release['sequence'],
                'confirmed': release_confirmed,
            },
            'started_at': self._state['started_at'],
            'observed_at': now,
            'elapsed_s': elapsed,
            'counters': dict(counters),
            'measurements': {
                'minimum_storage_free_bytes': minimum_free,
                'maximum_network_recovery_s': maximum_recovery,
                'network_outage_open': self._state['network_up'] is False,
                'maximum_consecutive_unhealthy': unhealthy,
                'maximum_allowed_consecutive_unhealthy':
                    profile['maximum_consecutive_unhealthy'],
            },
            'gates': gates,
            'promotion_ready': all(item['status'] == 'passed' for item in gates),
        }
        return result
