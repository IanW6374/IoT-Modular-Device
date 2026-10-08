"""Bounded durable mutation ledger. Requests are reserved before side effects."""
try:
    import ujson as json
    import uos as os
    import uhashlib as hashlib
    import ubinascii as binascii
except ImportError:
    import json
    import os
    import hashlib
    import binascii

MAX_OPERATIONS = 6
MAX_CLIENTS = 16
MAX_RESULT_BYTES = 384 * 1024
MAX_RESULT_STORAGE = 768 * 1024
TERMINAL = ('complete', 'failed', 'interrupted')


def digest(value):
    return binascii.hexlify(hashlib.sha256(value).digest()).decode()


class OperationError(RuntimeError):
    def __init__(self, code, message, status=409, operation_id=''):
        super().__init__(message)
        self.code, self.status, self.operation_id = code, status, operation_id


class OperationJournal:
    def __init__(self, namespace_factory, directory='/api-operations', boot_id=None):
        self.factory = namespace_factory
        self.directory = directory
        self.boot_id = boot_id or binascii.hexlify(os.urandom(8)).decode()
        try:
            os.mkdir(directory)
        except OSError:
            if not os.stat(directory)[0] & 0x4000:
                raise
        self.state = self._load()
        changed = False
        for record in self.state['records']:
            if record['boot'] != self.boot_id and record['state'] in ('running', 'queued'):
                record['state'] = 'interrupted'
                changed = True
        if changed:
            self._commit(self.state)
        retained = {item['id'] + '.json' for item in self.state['records']}
        for name in os.listdir(directory):
            stem = name.split('.', 1)[0]
            if (len(stem) == 24 and all(c in '0123456789abcdef' for c in stem)
                    and (name == stem + '.json.tmp' or
                         name == stem + '.json' and name not in retained)):
                os.remove(directory + '/' + name)

    def _load(self):
        namespace = self.factory()
        try:
            self.generation, payload = namespace.snapshot()
        finally:
            namespace.close()
        try:
            value = json.loads(payload.decode()) if payload else {'version': 1, 'clients': {}, 'records': []}
        except (ValueError, UnicodeError):
            raise OperationError('journal_invalid', 'Operation journal is invalid', 503)
        if (not isinstance(value, dict) or set(value) != {'version', 'clients', 'records'} or
                value['version'] != 1 or not isinstance(value['clients'], dict) or
                len(value['clients']) > MAX_CLIENTS or not isinstance(value['records'], list) or
                len(value['records']) > MAX_OPERATIONS):
            raise OperationError('journal_invalid', 'Operation journal is invalid', 503)
        for client, sequence in value['clients'].items():
            if (not isinstance(client, str) or len(client) != 64 or any(c not in '0123456789abcdef' for c in client)
                    or not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 9007199254740991):
                raise OperationError('journal_invalid', 'Operation client ledger is invalid', 503)
        for item in value['records']:
            if (not isinstance(item, dict) or set(item) != {'id', 'client', 'key', 'digest', 'state', 'status', 'boot', 'kind'} or
                    any(not isinstance(item[key], str) for key in ('id', 'client', 'key', 'digest', 'state', 'boot')) or
                    len(item['id']) != 24 or any(c not in '0123456789abcdef' for c in item['id']) or
                    item['client'] not in value['clients'] or
                    item['state'] not in ('running', 'queued', 'waiting_restart') + TERMINAL or
                    item['kind'] not in ('request', 'module_command') or
                    len(item['digest']) != 64 or any(c not in '0123456789abcdef' for c in item['digest']) or
                    len(item['boot']) > 32 or len(item['key']) > 49 or
                    not isinstance(item['status'], int) or not 100 <= item['status'] <= 599):
                raise OperationError('journal_invalid', 'Operation record is invalid', 503)
            parts = item['key'].split('.', 1)
            if (len(parts) != 2 or not parts[0].isdigit() or not 16 <= len(parts[1]) <= 32 or
                    any(c not in '0123456789abcdef' for c in parts[1]) or
                    not 1 <= int(parts[0]) <= value['clients'][item['client']] or
                    item['id'] != digest((item['client'] + ':' + item['key']).encode())[:24]):
                raise OperationError('journal_invalid', 'Operation request identity is invalid', 503)
        if len({item['id'] for item in value['records']}) != len(value['records']):
            raise OperationError('journal_invalid', 'Operation IDs are not unique', 503)
        return value

    def _commit(self, state):
        payload = json.dumps(state).encode()
        if len(payload) > 4096:
            raise OperationError('journal_full', 'Operation journal is full', 503)
        namespace = self.factory()
        try:
            generation = namespace.commit(self.generation, payload)
        finally:
            namespace.close()
        self.generation, self.state = generation, state

    def next_sequence(self, client):
        return self.state['clients'].get(client, 0) + 1

    def _path(self, identifier):
        return self.directory + '/' + identifier + '.json'

    def _record(self, identifier, client):
        for record in self.state['records']:
            if record['id'] == identifier and record['client'] == client:
                return record
        raise OperationError('operation_not_found', 'Operation is not retained for this client', 404)

    def reserve(self, client, key, method, path, body):
        if not isinstance(client, str) or len(client) != 64 or any(c not in '0123456789abcdef' for c in client):
            raise OperationError('invalid_client', 'Verified client fingerprint required', 403)
        parts = str(key or '').split('.', 1)
        if (len(parts) != 2 or not parts[0].isdigit() or len(parts[0]) > 16 or
                not 16 <= len(parts[1]) <= 32 or any(c not in '0123456789abcdef' for c in parts[1])):
            raise OperationError('idempotency_key_required', 'Idempotency-Key must be sequence.hex_nonce', 400)
        sequence = int(parts[0])
        if sequence < 1 or sequence > 9007199254740991:
            raise OperationError('invalid_request_sequence', 'Request sequence is out of range', 400)
        request_digest = digest(method.encode() + b'\n' + path.encode() + b'\n' + body)
        for record in self.state['records']:
            if record['client'] == client and record['key'] == key:
                if record['digest'] != request_digest:
                    raise OperationError('idempotency_conflict', 'Key was used with a different request', operation_id=record['id'])
                return dict(record), True
        if sequence < self.next_sequence(client):
            raise OperationError('request_sequence_expired', 'Request sequence is already consumed; reconcile, do not repeat the mutation')
        if client not in self.state['clients'] and len(self.state['clients']) >= MAX_CLIENTS:
            raise OperationError('journal_full', 'Operation client ledger is full', 503)
        state = json.loads(json.dumps(self.state))
        removed = None
        if len(state['records']) >= MAX_OPERATIONS:
            removed = next((item for item in state['records'] if item['state'] in TERMINAL), None)
            if removed is None:
                raise OperationError('operation_limit', 'All retained operations are still active', 503)
            state['records'].remove(removed)
        record = {'id': digest((client + ':' + key).encode())[:24], 'client': client,
                  'key': key, 'digest': request_digest, 'state': 'running',
                  'status': 202, 'boot': self.boot_id,
                  'kind': 'module_command' if path.split('?', 1)[0].startswith('/api/v3/modules/')
                      and path.split('?', 1)[0].endswith('/commands') else 'request'}
        state['clients'][client] = sequence
        state['records'].append(record)
        self._commit(state)
        if removed:
            try:
                os.remove(self._path(removed['id']))
            except OSError:
                pass
        return dict(record), False

    def update(self, identifier, client, status=None, state=None):
        document = json.loads(json.dumps(self.state))
        for record in document['records']:
            if record['id'] == identifier and record['client'] == client:
                if status is not None:
                    record['status'] = status
                if state is not None:
                    record['state'] = state
                if document != self.state:
                    self._commit(document)
                return self.public(record)
        raise OperationError('operation_not_found', 'Operation not found', 404)

    def finish(self, record, status, payload, state='complete'):
        encoded = json.dumps(payload).encode()
        if len(encoded) > MAX_RESULT_BYTES:
            raise OperationError('result_storage_full', 'Mutation result exceeds the retention limit', 503, record['id'])
        total = 0
        retained = {item['id'] + '.json' for item in self.state['records']}
        for name in os.listdir(self.directory):
            if name in retained and name != record['id'] + '.json':
                total += os.stat(self.directory + '/' + name)[6]
        for item in tuple(self.state['records']):
            if total + len(encoded) <= MAX_RESULT_STORAGE:
                break
            if item['state'] not in TERMINAL or item['id'] == record['id']:
                continue
            path = self._path(item['id'])
            try:
                size = os.stat(path)[6]
            except OSError:
                size = 0
            document = json.loads(json.dumps(self.state))
            document['records'] = [value for value in document['records'] if value['id'] != item['id']]
            self._commit(document)
            if size:
                os.remove(path)
                total -= size
        if total + len(encoded) > MAX_RESULT_STORAGE:
            raise OperationError('result_storage_full', 'Active operation results fill the retention limit', 503, record['id'])
        path = self._path(record['id'])
        if hasattr(os, 'statvfs'):
            storage = os.statvfs(self.directory)
            if storage[0] * storage[4] < len(encoded) + 64 * 1024:
                raise OperationError('result_storage_full', 'Insufficient space to record the outcome', 503, record['id'])
        with open(path + '.tmp', 'wb') as stream:
            stream.write(encoded)
            stream.flush()
        if hasattr(os, 'sync'):
            os.sync()
        os.rename(path + '.tmp', path)
        if hasattr(os, 'sync'):
            os.sync()
        return self.update(record['id'], record['client'], status, state)

    @staticmethod
    def public(record):
        return {'id': record['id'], 'status': record['state'],
                'request_status': record['status'], 'request_key': record['key'],
                'completion_scope': record['kind'],
                'retryable': False}

    def operation(self, identifier, client):
        return self.public(self._record(identifier, client))

    def result(self, identifier, client):
        record = self._record(identifier, client)
        if record['state'] == 'interrupted':
            raise OperationError('operation_interrupted', 'Outcome is uncertain after restart; do not repeat the mutation', operation_id=identifier)
        if record['state'] == 'running':
            raise OperationError('operation_in_progress', 'Operation outcome is not yet durable; reconcile without another write', operation_id=identifier)
        try:
            with open(self._path(identifier), 'rb') as stream:
                value = stream.read(MAX_RESULT_BYTES + 1)
        except OSError:
            raise OperationError('operation_in_progress', 'Operation outcome is not yet available; reconcile without another write', operation_id=identifier)
        if len(value) > MAX_RESULT_BYTES:
            raise OperationError('result_invalid', 'Stored operation result is invalid', 503, identifier)
        try:
            payload = json.loads(value.decode())
        except (ValueError, UnicodeError):
            raise OperationError('result_invalid', 'Stored operation result is invalid', 503, identifier)
        if not isinstance(payload, dict):
            raise OperationError('result_invalid', 'Stored operation result is invalid', 503, identifier)
        payload['operation'] = self.public(record)
        return record['status'], payload


def native_journal():
    from v3.runtime.iotmd_next.platform import Platform
    from v3.runtime.iotmd_next.storage import TransactionalNamespace
    platform = Platform()
    if not platform.capabilities()['security']['flash_encryption']:
        raise OperationError('encrypted_storage_required', 'Operation results require encrypted flash', 503)
    return OperationJournal(lambda: TransactionalNamespace(platform, 'apiops'))


_native_instance = None


def open_native_journal(logger):
    global _native_instance
    try:
        if _native_instance is None:
            _native_instance = native_journal()
        return _native_instance
    except Exception as exc:
        logger('API', 'Operation storage', {'log': 'Writes disabled - ' + str(exc)}, 'ERROR')
        return None
