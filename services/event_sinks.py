"""Adapters from structured application events to operational outputs."""


LEGACY_LOG_SEVERITY = {
    'ERROR': 0,
    'WARNING': 1,
    'INFO': 2,
    'DEBUG': 3,
}


def normalise_legacy_log_level(value):
    """Return a supported event severity without raising in the log path."""
    level = str(value or 'INFO').upper()
    return level if level in LEGACY_LOG_SEVERITY else 'INFO'


def should_emit_legacy_log(event_level, configured_level):
    """Compare event and configured levels without making logging fallible."""
    event = normalise_legacy_log_level(event_level)
    configured = normalise_legacy_log_level(configured_level)
    return LEGACY_LOG_SEVERITY[event] <= LEGACY_LOG_SEVERITY[configured]


class LegacyLogSink:
    """Bridge v2 events to the bounded portal/console/syslog log pipeline."""

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
