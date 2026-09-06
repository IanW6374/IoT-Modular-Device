"""Durable, generation-safe staging for authenticated v2 migrations."""

try:
    import ujson as json
except ImportError:
    import json


SECTIONS = ('credentials', 'module_settings', 'certificates_and_trust')
STATE_VERSION = 1


def _empty_state():
    return {
        'version': STATE_VERSION, 'next_handle': 1,
        'pending': None, 'handles': [],
    }


def _validate(value, maximum):
    if not isinstance(value, dict) or set(value) != set(_empty_state()):
        raise RuntimeError('migration staging registry is invalid')
    if value['version'] != STATE_VERSION:
        raise RuntimeError('migration staging registry version is unsupported')
    if (not isinstance(value['next_handle'], int) or
            isinstance(value['next_handle'], bool) or
            value['next_handle'] < 1 or value['next_handle'] > 2147483647):
        raise RuntimeError('migration staging handle counter is invalid')
    entries = value['handles']
    if not isinstance(entries, list) or len(entries) > maximum:
        raise RuntimeError('migration staging registry capacity is invalid')
    pending = value['pending']
    candidates = list(entries) + ([] if pending is None else [pending])
    seen = set()
    for entry in candidates:
        if not isinstance(entry, dict) or set(entry) != {'handle', 'section'}:
            raise RuntimeError('migration staging registry entry is invalid')
        handle = entry['handle']
        if (not isinstance(handle, int) or isinstance(handle, bool) or
                handle < 1 or handle in seen or entry['section'] not in SECTIONS):
            raise RuntimeError('migration staging registry entry is invalid')
        seen.add(handle)
    return value


def _encode(value, maximum):
    _validate(value, maximum)
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    except TypeError:
        return json.dumps(value).encode()


def _decode(payload, maximum):
    if not payload:
        return _empty_state()
    try:
        return _validate(json.loads(payload.decode()), maximum)
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError('migration staging registry is unreadable')


class ProductionMigrationStaging:
    """Keep migration material behind durable opaque handles.

    A handle intent is committed before native staging starts. If power is
    lost in that window, the next construction discards that exact handle
    before accepting more migration data.
    """

    def __init__(self, namespace, stager, activator, discarder, maximum=8):
        for value, name in (
                (stager, 'migration stager'), (activator, 'migration activator'),
                (discarder, 'migration discarder')):
            if not callable(value):
                raise ValueError(name + ' is unavailable')
        for operation in ('snapshot', 'commit'):
            if not callable(getattr(namespace, operation, None)):
                raise ValueError('migration staging namespace is unavailable')
        self._namespace = namespace
        self._stage = stager
        self._activate = activator
        self._discard = discarder
        self._maximum = max(3, min(16, int(maximum)))
        self._generation, payload = namespace.snapshot()
        self._state = _decode(payload, self._maximum)
        if not payload:
            self._commit()
        elif self._state['pending'] is not None:
            self._discard((self._state['pending']['handle'],))
            self._state['pending'] = None
            self._commit()

    def _commit(self):
        self._generation = self._namespace.commit(
            self._generation, _encode(self._state, self._maximum)
        )

    def stage(self, section, payload):
        if section not in SECTIONS:
            raise ValueError('migration section is invalid')
        if len(self._state['handles']) >= self._maximum:
            raise RuntimeError('migration staging capacity reached')
        handle = self._state['next_handle']
        self._state['next_handle'] = handle + 1
        self._state['pending'] = {'handle': handle, 'section': section}
        self._commit()
        try:
            result = self._stage(handle, section, payload)
            if result not in (None, True, handle):
                raise RuntimeError('migration stager rejected its durable handle')
        except Exception:
            try:
                self._discard((handle,))
            finally:
                self._state['pending'] = None
                self._commit()
            raise
        self._state['handles'].append(self._state['pending'])
        self._state['pending'] = None
        self._commit()
        return handle

    def _selected(self, handles):
        handles = tuple(handles)
        known = {entry['handle'] for entry in self._state['handles']}
        if (not handles or len(handles) > self._maximum or
                len(set(handles)) != len(handles) or
                any(handle not in known for handle in handles)):
            raise ValueError('migration handle set is invalid')
        return handles

    def _remove(self, handles):
        selected = set(handles)
        self._state['handles'] = [
            entry for entry in self._state['handles']
            if entry['handle'] not in selected
        ]
        self._commit()

    def activate(self, handles):
        handles = self._selected(handles)
        self._activate(handles)
        self._remove(handles)

    def discard(self, handles):
        handles = self._selected(handles)
        try:
            self._discard(handles)
        finally:
            self._remove(handles)

    def snapshot(self):
        return {
            'staged': len(self._state['handles']),
            'sections': sorted(set(
                entry['section'] for entry in self._state['handles']
            )),
            'pending_recovery': self._state['pending'] is not None,
        }
