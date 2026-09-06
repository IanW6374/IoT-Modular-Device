"""Generation-safe staging adapter for authenticated v2 migration payloads."""


class ProductionMigrationStaging:
    """Keep migration material behind opaque handles until trial confirmation."""

    def __init__(self, stager, activator, discarder, maximum=8):
        for value, name in (
                (stager, 'migration stager'), (activator, 'migration activator'),
                (discarder, 'migration discarder')):
            if not callable(value):
                raise ValueError(name + ' is unavailable')
        self._stage = stager
        self._activate = activator
        self._discard = discarder
        self._maximum = max(3, min(16, int(maximum)))
        self._handles = {}

    def stage(self, section, payload):
        if section not in (
                'credentials', 'module_settings', 'certificates_and_trust'):
            raise ValueError('migration section is invalid')
        if len(self._handles) >= self._maximum:
            raise RuntimeError('migration staging capacity reached')
        handle = self._stage(section, payload)
        if (not isinstance(handle, int) or isinstance(handle, bool) or
                handle < 1 or handle in self._handles):
            raise RuntimeError('migration stager returned an invalid handle')
        self._handles[handle] = section
        return handle

    def _selected(self, handles):
        handles = tuple(handles)
        if (not handles or len(handles) > self._maximum or
                len(set(handles)) != len(handles) or
                any(handle not in self._handles for handle in handles)):
            raise ValueError('migration handle set is invalid')
        return handles

    def activate(self, handles):
        handles = self._selected(handles)
        self._activate(handles)
        for handle in handles:
            del self._handles[handle]

    def discard(self, handles):
        handles = self._selected(handles)
        try:
            self._discard(handles)
        finally:
            for handle in handles:
                self._handles.pop(handle, None)

    def snapshot(self):
        return {
            'staged': len(self._handles),
            'sections': sorted(set(self._handles.values())),
        }
