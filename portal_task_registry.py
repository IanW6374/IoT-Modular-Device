"""Bounded, reconnectable portal task state for asynchronous device work."""

try:
    import time
except ImportError:
    time = None

_DOWNLOAD_CONTROL = {'active': False, 'discard': False}
from update_cancellation import UpdateCancelled


def _now():
    return int(time.time()) if time else 0


def start(tasks, name, coroutine, message, start_task, log_output):
    now_s = _now()
    tasks[name] = {
        'id': str(name), 'started_s': now_s, 'updated_s': now_s,
        'phase': 'running', 'message': str(message),
    }

    async def runner():
        try:
            result = await coroutine
        except Exception as exc:
            tasks[name].update({
                'phase': 'cancelled' if isinstance(exc, UpdateCancelled) else 'failed',
                'message': str(exc) or exc.__class__.__name__,
                'updated_s': _now(),
            })
            log_output(
                'Local', 'Task', {'log': name + ' stopped - ' + str(exc)},
                'INFO' if isinstance(exc, UpdateCancelled) else 'ERROR'
            )
        else:
            tasks[name].update({
                'phase': 'complete', 'percent': 100,
                'message': str(result or 'Complete'), 'updated_s': _now(),
            })

    start_task('portal_' + str(name), runner())
    return {'task_id': name, 'message': str(message)}


def status(tasks, name):
    return dict(tasks.get(
        str(name), {'phase': 'failed', 'message': 'Task was not found'}
    ))


def snapshot(tasks, limit=8):
    records = [dict(value) for value in tasks.values()]
    records.sort(key=lambda item: (
        1 if item.get('phase') == 'running' else 0,
        int(item.get('updated_s', 0) or 0),
    ), reverse=True)
    return records[:max(1, int(limit))]


def progress(tasks, name):
    labels = {
        'receiving': 'Downloading release',
        'writing': 'Writing core firmware',
        'verification': 'Verifying release',
    }

    async def report(phase, completed=0, total=0):
        total = int(total or 0)
        completed = int(completed or 0)
        record = tasks.setdefault(name, {'id': str(name), 'started_s': _now()})
        record.update({
            'phase': 'running',
            'message': labels.get(str(phase), str(phase).replace('_', ' ')),
            'percent': max(0, min(100, int(completed * 100 / total)))
            if total else 0,
            'updated_s': _now(),
        })

    return report


def cancellable_progress(control, report=None):
    """Wrap an optional progress reporter with a shared cancellation flag."""
    async def notify(*values):
        if control.get('discard'):
            raise UpdateCancelled('update was discarded')
        if report:
            result = report(*values)
            if result is not None:
                await result
    return notify


def discard_update(discard):
    """Request cancellation and discard any already staged update state."""
    active = bool(_DOWNLOAD_CONTROL.get('active'))
    _DOWNLOAD_CONTROL['discard'] = active
    if active:
        return 'Update discard requested'
    discarded = discard()
    return 'Staged upgrade discarded' if discarded else 'No staged upgrade to discard'


def download_active():
    return bool(_DOWNLOAD_CONTROL.get('active'))


def begin_cancellable(report=None):
    if download_active():
        raise ValueError('another update is already in progress')
    _DOWNLOAD_CONTROL.update({'active': True, 'discard': False})
    return cancellable_progress(_DOWNLOAD_CONTROL, report)


def finish_cancellable(discard):
    cancelled = bool(_DOWNLOAD_CONTROL.get('discard'))
    _DOWNLOAD_CONTROL.update({'active': False, 'discard': False})
    if cancelled:
        discard()
        raise UpdateCancelled('update was discarded')
