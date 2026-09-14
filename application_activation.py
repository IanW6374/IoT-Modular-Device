"""Constrained-filesystem application activation for the frozen supervisor."""

import os

import update_support
from application_storage import (
    _copy_file, _file_exists, _remove_if_exists, _remove_tree,
    _skip_stream, _write_json_atomic, _write_stream_file,
)


MEMORY_RESERVE = 512 * 1024


class _BytesReader:
    """Sequential reader that does not duplicate the PSRAM bundle buffer."""

    def __init__(self, payload):
        self.payload = payload
        self.offset = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self.payload) - self.offset
        end = min(len(self.payload), self.offset + int(size))
        value = self.payload[self.offset:end]
        self.offset = end
        return value

    def close(self):
        self.payload = None


def _layout(app, state, manifest):
    selected_paths = set(state.get('selected_paths', ()))
    selected_size = sum(
        int(entry.get('size', 0)) for entry in manifest.get('files', [])
        if app._safe_path(entry.get('path', '')) in selected_paths
    )
    backup_size = 0
    for path in selected_paths:
        if app.is_shared_path(path) and _file_exists(path):
            try:
                backup_size += int(os.stat(path)[6])
            except Exception:
                pass
    current_slot = app.active_slot()
    target_slot = ''
    if state.get('has_application'):
        target_slot = 'b' if current_slot == 'a' else 'a'
    return selected_paths, selected_size + backup_size, current_slot, target_slot


def _memory_available(app, required):
    """Confirm deleting the verified bundle can safely fund extraction."""
    status = update_support.storage_status()
    try:
        bundle_size = int(os.stat(app.BUNDLE_PATH)[6])
    except Exception:
        bundle_size = 0
    if (
        status.get('available') and
        int(status.get('free_bytes', 0)) + bundle_size <
        int(required) + update_support.DEFAULT_STORAGE_RESERVE
    ):
        raise ValueError(
            'insufficient storage after releasing the verified application bundle'
        )
    try:
        import gc
        available = getattr(gc, 'mem_free', lambda: 0)()
        if available and available < bundle_size + MEMORY_RESERVE:
            raise ValueError(
                'insufficient memory for constrained application activation'
            )
    except ImportError:
        pass
    return bundle_size


def prepare_capacity(app):
    """Fail before core selection unless the application can be extracted."""
    state = app.update_status()
    if state.get('status') != 'ready':
        raise ValueError('no staged application update')
    manifest = app.validate_bundle(
        app.BUNDLE_PATH, state.get('allow_protected', False)
    )
    unused, required, unused_current, target_slot = _layout(
        app, state, manifest
    )
    if target_slot:
        _remove_tree(app._slot_path(target_slot))
    try:
        update_support.require_free_space(required)
        return 'filesystem'
    except ValueError as exc:
        if not str(exc).startswith('insufficient storage:'):
            raise
        _memory_available(app, required)
        return 'memory'


def activate(app):
    state = app.update_status()
    if state.get('status') == 'trial':
        app.rollback_update()
        return 'rolled back unconfirmed update'
    if state.get('status') == 'activating':
        app.rollback_update()
        return 'rolled back interrupted update'
    if state.get('status') == 'committing':
        app._finish_commit(state)
        return 'completed interrupted update confirmation'
    if state.get('status') != 'ready':
        return ''

    manifest = app.validate_bundle(
        app.BUNDLE_PATH, state.get('allow_protected', False)
    )
    selected_for_update, required, current_slot, target_slot = _layout(
        app, state, manifest
    )
    if target_slot:
        _remove_tree(app._slot_path(target_slot))
    source = 'filesystem'
    try:
        update_support.require_free_space(required)
    except ValueError as exc:
        if not str(exc).startswith('insufficient storage:'):
            raise
        _memory_available(app, required)
        source = 'memory'

    payload = None
    if source == 'memory':
        try:
            with open(app.BUNDLE_PATH, 'rb') as stream:
                payload = stream.read()
        except MemoryError:
            raise ValueError(
                'insufficient memory for constrained application activation'
            )

    state['status'] = 'activating'
    state['applied'] = []
    state['previous_slot'] = current_slot
    state['target_slot'] = target_slot
    _write_json_atomic(app.STATE_PATH, state)

    if payload is not None:
        _remove_if_exists(app.BUNDLE_PATH)
        update_support.require_free_space(required)
        stream = _BytesReader(payload)
    else:
        stream = open(app.BUNDLE_PATH, 'rb')
    try:
        app.read_manifest(stream)
        configured_paths = state.get('selected_paths')
        selected_paths = (
            set(configured_paths) if configured_paths is not None else
            {
                app._safe_path(entry.get('path', ''))
                for entry in manifest.get('files', [])
            }
        )
        for entry in manifest['files']:
            path = app._safe_path(entry['path'])
            size = int(entry['size'])
            if path not in selected_paths:
                _skip_stream(stream, size, path)
            elif app.is_shared_path(path):
                backup_path = app.BACKUP_ROOT + '/' + path
                existed = _file_exists(path)
                if existed:
                    _copy_file(path, backup_path)
                state['applied'].append({'path': path, 'existed': existed})
                _write_json_atomic(app.STATE_PATH, state)
                _write_stream_file(stream, size, path)
            elif target_slot:
                _write_stream_file(
                    stream, size, app._slot_path(target_slot, path)
                )
            else:
                _skip_stream(stream, size, path)
    finally:
        stream.close()
        payload = None

    if target_slot and not _file_exists(
        app._slot_path(target_slot, app.APPLICATION_ENTRY)
    ):
        raise ValueError('application bundle has no ' + app.APPLICATION_ENTRY)

    if target_slot:
        integrity_entries = []
        for entry in manifest.get('files', []):
            path = app._safe_path(entry.get('path', ''))
            if path in selected_paths and not app.is_shared_path(path):
                integrity_entries.append({
                    'path': path, 'size': int(entry.get('size', 0)),
                    'sha256': str(entry.get('sha256', '')).lower()
                })
        _write_json_atomic(
            app._slot_path(target_slot, app.SLOT_INTEGRITY_FILE),
            {'files': integrity_entries}
        )
        if not app.validate_slot_integrity(target_slot):
            raise ValueError('application slot integrity verification failed')

    state['status'] = 'trial'
    _write_json_atomic(app.STATE_PATH, state)
    update_support.record_update_event(
        'application', 'trial', state.get('version', ''),
        digest=str(manifest.get('signature', ''))
    )
    return 'activated update ' + str(state.get('version', ''))
