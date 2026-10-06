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
        values.update(normalized.get('secrets', {}))
        if 'timezone_name' in values:
            values['timezone_offset_minutes'] = self.timezone.offset_minutes(
                values['timezone_name']
            )
        self.credentials.preview_operational_settings(values)
        network_keys = {
            'wifi_ssid', 'wifi_password', 'wifi_dhcp', 'wifi_ip_address',
            'wifi_subnet_mask', 'wifi_gateway', 'wifi_dns_server',
        }
        network_trial = bool(network_keys.intersection(values))
        updated = (
            self.credentials.update_operational_settings(values, True)
            if network_trial else
            self.credentials.update_operational_settings(values)
        )
        updated = updated or {}
        fields = sorted(
            list(normalized['settings']) + list(normalized.get('secrets', {}))
        )
        self.health.record_event(
            'configuration_profile_applied', normalized['name'], {
                'actor': str(actor)[:64], 'fields': ','.join(fields),
            }, force=True, component='configuration'
        )
        needs_restart = bool(set(values) - {'device_description'})
        if needs_restart:
            self.restart_required('Configuration profile applied')
        return {
            'name': normalized['name'], 'applied_settings': fields,
            'restart_required': needs_restart,
            'network_trial_pending': bool(
                updated.get('network_trial_pending', False)
            ),
        }
