"""Device-owned update lifecycles, independent of the API mutation ledger.

Two fixed-size files live on the encrypted VFS. Capacity is reserved before
admission; only lifecycle boundaries are flushed, not transfer percentages.
The generic API ledger and its protected anti-replay watermarks are untouched.
"""
try:
    import ujson as json
except ImportError:
    import json
try:
    import uos as os
except ImportError:
    import os
try:
    import uhashlib as hashlib
except ImportError:
    import hashlib
from binascii import hexlify

CONTRACT = 1
SLOT_BYTES = 8192
RETAINED = 4
PHASES = ('queued', 'inspect', 'core_write', 'core_verify',
          'application_download', 'application_verify', 'pair', 'install', 'complete')
TERMINAL = ('complete', 'failed', 'cancelled', 'interrupted')
STATES = ('prepared', 'accepted', 'checking', 'staging', 'staged', 'scheduled',
          'installing', 'cancelling') + TERMINAL
TRANSITIONS = {
    'prepared': ('accepted', 'interrupted'),
    'accepted': ('checking', 'cancelling', 'failed', 'interrupted'),
    'checking': ('staging', 'cancelling', 'failed', 'interrupted'),
    'staging': ('staging', 'staged', 'cancelling', 'failed', 'interrupted'),
    'staged': ('scheduled', 'installing', 'cancelling', 'failed', 'interrupted'),
    'scheduled': ('installing', 'cancelling', 'failed', 'interrupted'),
    'installing': ('complete', 'failed', 'interrupted'),
    'cancelling': ('cancelled', 'interrupted'),
}


def _copy(value):
    return json.loads(json.dumps(value))


def _digest(payload):
    return hexlify(hashlib.sha256(payload).digest()).decode()


def _flush(stream):
    stream.flush()
    if hasattr(os, 'fsync'):
        os.fsync(stream.fileno())
    elif hasattr(os, 'sync'):
        os.sync()
    else:
        raise RuntimeError('Durable filesystem flush is unavailable')


def operation_plan(policy):
    """The ID is an existing *signed* command ID; no unsigned extension fields."""
    commands = policy.get('commands') or []
    if not commands:
        return None
    actions = [item['action'] for item in commands]
    if actions not in (['check-update', 'download-update'],
                       ['check-update', 'download-update', 'activate-update']):
        raise ValueError('Update operations require a check/download[/activate] plan')
    first = commands[0]
    identifier = first['id']
    if (len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier)):
        raise ValueError('Update operation ID must be 128-bit lowercase hex')
    sequence = first['release_sequence']
    kind = first.get('release_type')
    if sequence <= 0 or kind not in ('application', 'firmware', 'universal'):
        raise ValueError('Update operation requires an explicit signed release')
    if any(item['release_sequence'] != sequence or item.get('release_type') != kind
           for item in commands):
        raise ValueError('Update operation commands must reference the same release')
    return {'id': identifier, 'release_sequence': sequence, 'release_type': kind,
            'policy_sequence': policy['policy_sequence'],
            'activation': 'install' if len(commands) == 3 else 'stage',
            'command_ids': [item['id'] for item in commands]}


class UpdateOperations:
    def __init__(self, device_id, path='.update-operations', boot_id=None):
        self.device_id = str(device_id)
        self.path = str(path)
        self.boot_id = boot_id or hexlify(os.urandom(8)).decode()
        self.state = {'contract': CONTRACT, 'generation': 0, 'watermark': 0,
                      'boot_id': '', 'boot_epoch': 0, 'records': []}
        self.slot = None
        self.loaded = False
        self.samples = {}
        self.sample_sequence = 0

    def _read(self, slot):
        with open(self.path + '.' + str(slot), 'rb') as stream:
            raw = stream.read(SLOT_BYTES + 1)
        if len(raw) != SLOT_BYTES:
            raise ValueError('Update journal slot size is invalid')
        header, raw = raw.split(b'\n', 1)
        size, checksum = header.decode().split(':')
        size = int(size)
        if not 0 < size <= SLOT_BYTES - 80:
            raise ValueError('Update journal payload is invalid')
        payload = raw[:size]
        if _digest(payload) != checksum:
            raise ValueError('Update journal checksum is invalid')
        value = json.loads(payload.decode())
        if (value.get('contract') != CONTRACT or not isinstance(value.get('generation'), int)
                or not isinstance(value.get('watermark'), int)
                or not isinstance(value.get('records'), list) or len(value['records']) > RETAINED):
            raise ValueError('Update journal contract is invalid')
        for record in value['records']:
            if record.get('state') not in STATES or record.get('device_id') != self.device_id:
                raise ValueError('Update journal record is invalid')
        return value

    def open(self):
        if self.loaded:
            return
        valid = []
        exists = False
        for slot in (0, 1):
            try:
                os.stat(self.path + '.' + str(slot))
                exists = True
                valid.append((self._read(slot), slot))
            except (ValueError, OSError):
                pass
        if valid:
            self.state, self.slot = max(valid, key=lambda item: item[0]['generation'])
        elif exists:
            # Never turn damaged/unknown state into permission to repeat effects.
            raise RuntimeError('Update journal is unreadable; local recovery is required')
        else:
            for slot in (0, 1):
                with open(self.path + '.' + str(slot), 'wb') as stream:
                    stream.write(b'\0' * SLOT_BYTES)
                    _flush(stream)
            self._commit(self.state)
        # Repair/reserve the alternate slot before permitting a new admission.
        for slot in (0, 1):
            try:
                size = os.stat(self.path + '.' + str(slot))[6]
            except OSError:
                size = -1
            if size != SLOT_BYTES:
                with open(self.path + '.' + str(slot), 'wb') as stream:
                    stream.write(b'\0' * SLOT_BYTES)
                    _flush(stream)
        self.loaded = True

    def _commit(self, value):
        value = _copy(value)
        value['generation'] = self.state['generation'] + 1
        payload = json.dumps(value).encode()
        if len(payload) > SLOT_BYTES - 80:
            raise RuntimeError('Update journal capacity exceeded before dispatch')
        header = (str(len(payload)) + ':' + _digest(payload) + '\n').encode()
        raw = header + payload
        raw += b'\0' * (SLOT_BYTES - len(raw))
        slot = 0 if self.slot != 0 else 1
        try:
            with open(self.path + '.' + str(slot), 'r+b') as stream:
                if stream.write(raw) != SLOT_BYTES:
                    raise OSError('Short update journal write')
                _flush(stream)
            checked = self._read(slot)
            if checked != value:
                raise OSError('Update journal readback failed')
        except Exception:
            # Even if a flush succeeded before raising, this process must not
            # overwrite an ambiguously committed newer generation.
            self.loaded = False
            raise
        self.state, self.slot = value, slot

    def active(self):
        self.open()
        return next((item for item in reversed(self.state['records'])
                     if item['state'] not in TERMINAL), None)

    def start_boot(self):
        self.open()
        if self.state['boot_id'] != self.boot_id:
            value = _copy(self.state)
            value.update(boot_id=self.boot_id, boot_epoch=value['boot_epoch'] + 1)
            self._commit(value)

    def prepare(self, policy, report_key=None, reporting=None):
        self.open()
        plan = operation_plan(policy)
        active = self.active()
        if active:
            raise ValueError('An update operation is already active; reconcile or cancel it first')
        if plan is None:
            return None
        if report_key is not None and (not isinstance(report_key, str) or len(report_key) != 64
                or any(c not in '0123456789abcdef' for c in report_key)):
            raise ValueError('Update report authentication key is invalid')
        if plan['policy_sequence'] <= self.state['watermark']:
            raise ValueError('Update operation admission sequence is not newer')
        if any(item['id'] == plan['id'] for item in self.state['records']):
            raise ValueError('Update operation ID is already retained; read its result instead')
        record = dict(plan, device_id=self.device_id, state='prepared', phase='queued',
                      revision=1, completed=['queued'], detail='Admission prepared')
        if report_key:
            record['report_key'] = report_key
            record['reporting'] = reporting
        value = _copy(self.state)
        value['watermark'] = plan['policy_sequence']
        value['records'] = (value['records'] + [record])[-RETAINED:]
        self._commit(value)
        return record['id']

    def recover_admission(self, policy):
        record = self.active()
        if not record or record['state'] != 'prepared':
            return
        plan = operation_plan(policy) if policy else None
        if plan and all(record.get(key) == value for key, value in plan.items()):
            self.transition('accepted', detail='Signed admission committed')
        else:
            self.transition('interrupted', detail='Admission did not commit; no update dispatched')

    def transition(self, state, phase=None, detail='', completed=None):
        if state not in STATES:
            raise ValueError('Invalid update operation state')
        record = self.active()
        if record is None:
            return
        if state != record['state'] and state not in TRANSITIONS.get(record['state'], ()):
            raise ValueError('Invalid update operation transition')
        phase = phase or record['phase']
        if phase not in PHASES:
            raise ValueError('Invalid update operation phase')
        if PHASES.index(phase) < PHASES.index(record['phase']):
            raise ValueError('Update operation phase cannot regress')
        value = _copy(self.state)
        current = value['records'][-1]
        done = list(current['completed'])
        for name in completed or ():
            if name not in PHASES:
                raise ValueError('Invalid completed update phase')
            if name not in done:
                done.append(name)
        if state == 'complete':
            if record['state'] != 'installing':
                raise ValueError('Only confirmed installation can complete an operation')
            done = list(PHASES)
            phase = 'complete'
        detail = ''.join(c if ord(c) >= 32 else ' ' for c in str(detail))[:160]
        if (current['state'], current['phase'], current['detail'], current['completed']) == (state, phase, detail, done):
            return
        current.update(state=state, phase=phase, detail=detail, completed=done,
                       revision=current['revision'] + 1)
        self._commit(value)
        self.samples.pop(record['id'], None)

    def progress(self, phase, percent, completed):
        record = self.active()
        if not record or record['state'] in ('prepared', 'cancelling', 'installing'):
            return
        self.transition('staging', phase, 'Staging signed release', completed)
        self.sample_sequence += 1
        self.samples[record['id']] = (self.sample_sequence, min(100, max(0, int(percent))))

    def snapshot(self, identifier):
        self.open()
        record = next((item for item in self.state['records'] if item['id'] == identifier), None)
        if record is None:
            raise KeyError('Update operation is not retained; absence is not a job outcome')
        result = _copy(record)
        result.pop('report_key', None)
        result.pop('reporting', None)
        result.update(contract=CONTRACT, boot_id=self.boot_id, boot_epoch=self.state['boot_epoch'])
        sample, percent = self.samples.get(identifier, (0, None))
        result['sample_sequence'] = sample
        result['percent'] = percent if record['state'] == 'staging' else None
        return result

    def recover_execution(self, application_sequence, firmware_sequence, components_idle):
        """Called *after* local startup health/paired confirmation, never by GET."""
        record = self.active()
        if not record:
            return
        if record['state'] == 'installing':
            sequence, kind = record['release_sequence'], record['release_type']
            exact = ((kind == 'firmware' or application_sequence == sequence) and
                     (kind == 'application' or firmware_sequence == sequence))
            if exact and components_idle:
                self.transition('complete', detail='Installed and confirmed by local startup health')
            else:
                self.transition('interrupted', detail='Installation not confirmed; inspect device recovery state')
        elif record['state'] in ('checking', 'staging'):
            self.transition('interrupted', detail='Device restarted during staging; no automatic command replay')

    def command_allowed(self, command):
        record = self.active()
        return bool(record and record['state'] not in ('prepared', 'cancelling', 'installing') and
                    command.get('id') in record['command_ids'])


def staged_component_ready(record, application, firmware, universal):
    component = {'application': application, 'firmware': firmware, 'universal': universal}[record['release_type']]
    state = component.update_status()
    return state.get('status') == 'ready' and int(state.get('release_sequence', 0)) == record['release_sequence']


class UpdateOperationRunner:
    """Single device-owned worker; callbacks retain existing verified installers."""
    def __init__(self, operations, fleet, check, download, activate, staged_ready,
                 cancellation_status):
        self.operations = operations
        self.fleet = fleet
        self.check = check
        self.download = download
        self.activate = activate
        self.staged_ready = staged_ready
        self.cancellation_status = cancellation_status

    def recover(self, application_sequence, firmware_sequence, components_idle):
        self.operations.start_boot()
        self.operations.recover_admission(self.fleet.state.get('policy'))
        self.operations.recover_execution(application_sequence, firmware_sequence, components_idle)
        record = self.operations.active()
        if record and record['state'] in ('staged', 'scheduled') and not self.staged_ready(record):
            self.operations.transition('interrupted', detail='Verified staged components are unavailable after restart')

    async def tick(self):
        record = self.operations.active()
        if not record:
            return
        identifier = record['id']
        if record['state'] == 'cancelling':
            if self.cancellation_status().get('status') == 'cancelled':
                self.operations.transition('cancelled', detail='Staging stopped and staged data discarded')
            return
        if record['state'] in ('prepared', 'installing'):
            return
        try:
            if record['state'] == 'accepted':
                self.operations.transition('checking', 'inspect', 'Checking signed release applicability')
                channel = ((self.fleet.state.get('policy') or {}).get('updates') or {}).get('channel')
                result = await self.check(channel, record['release_sequence'], record['release_type'])
                current = self.operations.active()
                if not current or current['id'] != identifier or current['state'] == 'cancelling':
                    return
                if str(result).startswith('No newer compatible release'):
                    raise ValueError(str(result))
                self.operations.transition('staging', 'inspect', 'Staging signed release', ['queued', 'inspect'])
                await self.download()
                current = self.operations.active()
                if not current or current['id'] != identifier or current['state'] == 'cancelling':
                    return
                if not self.staged_ready(current):
                    raise ValueError('Staging did not produce the requested verified components')
                self.operations.transition('staged', 'pair', 'Signed components verified and staged', PHASES[:7])
                record = self.operations.active()
            if record['state'] in ('staged', 'scheduled') and record['activation'] == 'install':
                if not self.fleet.within_maintenance_window():
                    if record['state'] != 'scheduled':
                        self.operations.transition('scheduled', detail='Staged; waiting for the signed maintenance window')
                    return
                if not self.staged_ready(record):
                    raise ValueError('Requested verified components are no longer staged')
                self.operations.transition('installing', 'install', 'Activation dispatched; awaiting local health confirmation')
                result = self.activate(record)
                if 'failed' in str(result).lower():
                    raise ValueError(str(result))
        except Exception as exc:
            current = self.operations.active()
            if current and current['id'] == identifier and current['state'] == 'cancelling':
                if self.cancellation_status().get('status') == 'cancelled':
                    self.operations.transition('cancelled', detail='Staging stopped and staged data discarded')
                return  # Deliberate cancellation is not an upgrade error.
            if current and current['id'] == identifier and current['state'] not in ('prepared', 'cancelling'):
                # A storage/activation failure is not proof that effects did
                # not execute. Keep it explicitly unresolved, never replay.
                terminal = 'interrupted' if current['state'] == 'installing' or isinstance(exc, OSError) else 'failed'
                self.operations.transition(terminal, detail=str(exc))
            raise
