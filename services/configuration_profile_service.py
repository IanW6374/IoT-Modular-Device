"""Application service for validated remote configuration profiles."""

import configuration_profiles


class ConfigurationProfileService:
    def __init__(self, credentials, timezone, health, restart_required):
        self.credentials = credentials
        self.timezone = timezone
        self.health = health
        self.restart_required = restart_required

    def apply(self, profile, actor='Management Suite'):
        normalized = configuration_profiles.normalize_profile(profile)
        values = dict(normalized['settings'])
        if 'timezone_name' in values:
            values['timezone_offset_minutes'] = self.timezone.offset_minutes(
                values['timezone_name']
            )
        self.credentials.preview_operational_settings(values)
        self.credentials.update_operational_settings(values)
        fields = sorted(normalized['settings'])
        self.health.record_event(
            'configuration_profile_applied', normalized['name'], {
                'actor': str(actor)[:64], 'fields': ','.join(fields),
            }, force=True, component='configuration'
        )
        self.restart_required('Configuration profile applied')
        return {
            'name': normalized['name'], 'applied_settings': fields,
            'restart_required': True,
        }
