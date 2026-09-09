"""Local boot-health gates and paired update confirmation."""

from application.boot_health import evaluate


class StartupService:
    def __init__(self, platform, boot, lifecycle, health, log_output,
                 qualification=None):
        self.platform = platform
        self.boot = boot
        self.lifecycle = lifecycle
        self.health = health
        self.log_output = log_output
        self.qualification = qualification

    def start_watchdog(self, factory, timeout_ms, progress_callback=None,
                       progress_setter=None):
        if not timeout_ms:
            return None, True
        if factory is None:
            return None, False
        timeout_ms = self.platform.watchdog_timeout(timeout_ms)
        watchdog = factory(timeout=timeout_ms)
        if progress_setter and progress_callback:
            progress_setter(progress_callback)
        self.log_output(
            'Local', 'Watchdog',
            {'log': 'Enabled: ' + str(timeout_ms) + ' ms'}, 'INFO'
        )
        return watchdog, True

    def check(self, free_heap, minimum_free_heap, required_services,
              service_states, watchdog_required=False, watchdog_ready=False):
        self.boot.stage('essential-services', device_state='initialising')
        result = evaluate(
            self.platform.capabilities(), free_heap, minimum_free_heap,
            required_services, service_states, watchdog_required, watchdog_ready
        )
        self.boot.stage('health-check', durable=True)
        if result['healthy']:
            return result
        detail = '; '.join(result['failures'])
        self.lifecycle.transition('failed', detail)
        self.health.record_event(
            'activation_health_failed', detail, result,
            force=True, severity='critical', component='startup'
        )
        self.boot.fail(detail)
        self.log_output(
            'Local', 'Update health',
            {'log': 'Activation health check failed: ' + detail}, 'ERROR'
        )
        return result

    def confirm_updates(self, firmware_update, app_update, universal_update,
                        recovery_boot):
        firmware_confirmed = False
        application_confirmed = False
        universal_state = universal_update.update_status()
        native_pair = universal_state.get('status') == 'activating'
        if native_pair:
            try:
                application_required = bool(
                    universal_state.get('application_required', True)
                )
                firmware_required = bool(
                    universal_state.get('firmware_required', True)
                )
                application_already_confirmed = (
                    application_required and
                    app_update.update_status().get('status') == 'idle' and
                    app_update.running_release_sequence() == int(
                        universal_state.get('application_sequence', 0)
                    )
                )
                application_prepared = True
                if application_required and not application_already_confirmed:
                    application_prepared = app_update.confirm_update(True)
                if not application_prepared:
                    raise RuntimeError('runtime trial is unavailable')
                if application_required:
                    self.log_output(
                        'Local', 'Application update',
                        {'log': 'Runtime slot passed local health check'}, 'INFO'
                    )
                universal_update.record_confirmation_phase('runtime-healthy')
                # Keep the durable application pointer on the previously
                # confirmed slot until ESP-IDF has made the matching core
                # non-rollbackable.  If power is lost or native confirmation
                # fails, the frozen supervisor can still discard the trial
                # application without needing code from the rejected core.
                if not universal_update.confirm_native_pair():
                    raise RuntimeError('native paired trial is unavailable')
                universal_update.record_confirmation_phase('platform-confirmed')
                if firmware_required:
                    firmware_committed = (
                        firmware_update.confirm_after_native_pair() or
                        firmware_update.running_release_sequence() == int(
                            universal_state.get('firmware_sequence', 0)
                        )
                    )
                    if not firmware_committed:
                        raise RuntimeError('core confirmation metadata is unavailable')
                    firmware_confirmed = True
                universal_update.record_confirmation_phase('platform-metadata')
                if application_required and not application_already_confirmed:
                    if not app_update.confirm_update():
                        raise RuntimeError('runtime confirmation commit failed')
                    application_already_confirmed = True
                universal_update.record_confirmation_phase('runtime-committed')
                application_confirmed = application_required
                self.log_output(
                    'Local', 'Universal update',
                    {'log': 'Native platform/runtime pair confirmed atomically'},
                    'INFO'
                )
            except Exception as exc:
                universal_update.record_confirmation_failure(exc)
                self.log_output(
                    'Local', 'Universal update',
                    {'log': 'Could not confirm native pair - ' + str(exc)},
                    'ERROR'
                )
                try:
                    universal_update.rollback_native_pair(
                        'paired confirmation failed: ' + str(exc)
                    )
                except Exception:
                    pass
                return firmware_confirmed, application_confirmed
            if universal_update.confirm_update():
                self.log_output(
                    'Local', 'Universal update',
                    {'log': 'Core and application update confirmed healthy'},
                    'INFO'
                )
            marker = getattr(recovery_boot, 'mark_application_healthy', None)
            if marker:
                marker()
            return firmware_confirmed, application_confirmed
        try:
            if firmware_update.confirm_update():
                firmware_confirmed = True
                self.log_output(
                    'Local', 'Base firmware',
                    {'log': 'OTA partition confirmed after local health check'},
                    'INFO'
                )
        except Exception as exc:
            self.log_output(
                'Local', 'Base firmware',
                {'log': 'Could not confirm OTA partition - ' + str(exc)}, 'ERROR'
            )
        if app_update.confirm_update():
            application_confirmed = True
            self.log_output(
                'Local', 'Application update',
                {'log': 'Update confirmed healthy'}, 'INFO'
            )
        if universal_update.confirm_update():
            self.log_output(
                'Local', 'Universal update',
                {'log': 'Core and application update confirmed healthy'}, 'INFO'
            )
        marker = getattr(recovery_boot, 'mark_application_healthy', None)
        if marker:
            marker()
        return firmware_confirmed, application_confirmed

    def finalise(self, state, ntp_ready, api_enabled, api_server,
                 mqtt_configured, mqtt_started):
        self.lifecycle.transition('running')
        state.set('phase', 'running')
        degraded = []
        if not ntp_ready:
            degraded.append('NTP unavailable')
        if api_enabled and api_server is None:
            degraded.append('Device API unavailable')
        if mqtt_configured and not mqtt_started:
            degraded.append('MQTT unavailable')
        if degraded:
            reason = '; '.join(degraded)
            self.lifecycle.degrade(reason)
            # External services may be unavailable while the local runtime is
            # nevertheless healthy and fully recoverable. Close the boot
            # transaction before retaining the degraded detail so a later
            # power-cycle can be counted as a successful recovery.
            self.boot.healthy('degraded')
            self.boot.degrade(reason)
        else:
            self.boot.healthy()
        previous = getattr(self.boot, 'previous_snapshot', lambda: None)()
        if self.qualification and self.qualification.record_successful_boot(
                self.boot.snapshot(), previous):
            self.health.record_event(
                'power_recovery_qualified',
                'Power-on boot recovered to a healthy running state',
                force=True, component='qualification'
            )
        return 'degraded' if degraded else 'running'
