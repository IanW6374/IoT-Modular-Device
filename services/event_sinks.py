"""Adapters from structured application events to operational outputs."""


LOG_SEVERITY = {
    'ERROR': 0,
    'WARNING': 1,
    'INFO': 2,
    'DEBUG': 3,
}


def normalise_log_level(value):
    """Return a supported event severity without raising in the log path."""
    level = str(value or 'INFO').upper()
    return level if level in LOG_SEVERITY else 'INFO'


def should_emit_log(event_level, configured_level):
    """Compare event and configured levels without making logging fallible."""
    event = normalise_log_level(event_level)
    configured = normalise_log_level(configured_level)
    return LOG_SEVERITY[event] <= LOG_SEVERITY[configured]


class RuntimeLogSink:
    """Bridge structured events to the bounded portal/console/syslog pipeline."""

    LEVELS = {
        'debug': 'DEBUG', 'info': 'INFO', 'warning': 'WARNING',
        'error': 'ERROR', 'critical': 'ERROR',
    }

    def __init__(self, logger):
        self.logger = logger

    def write(self, event):
        event = event or {}
        component = str(event.get('component') or 'runtime')
        kind = str(event.get('kind') or 'event')
        message = str(event.get('message') or event.get('detail') or '')
        self.logger(
            'Local', component + ' ' + kind,
            {'log': message or kind},
            self.LEVELS.get(str(event.get('severity') or 'info').lower(), 'INFO')
        )
