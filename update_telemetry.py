"""Read-only, bounded release progress for Management's deployment view."""


class UpdateTelemetry:
    def __init__(self):
        self.progress = {}

    def begin(self, release):
        self.progress = {
            'release_sequence': int(release.get('release_sequence', 0)),
            'type': str(release.get('type', '')),
            'phase': 'inspect', 'percent': 0, 'completed': ['queued', 'inspect'],
        }

    def record(self, phase, completed, total):
        if not self.progress:
            return
        phases = {
            'firmware_writing': 'core_write',
            'firmware_verification': 'core_verify',
            'application_receiving': 'application_download',
            'application_verification': 'application_verify',
            'application_compacting': 'application_download',
            'complete': 'pair',
        }
        step = phases.get(str(phase))
        if not step:
            return
        order = ('queued', 'inspect', 'core_write', 'core_verify',
                 'application_download', 'application_verify', 'pair')
        done = self.progress['completed']
        for previous in order[:order.index(step)]:
            if previous not in done:
                done.append(previous)
        percent = min(100, max(0, int(completed * 100 / total))) if total else 0
        # A 100% byte counter isn't a successful signature/flash verification.
        # Complete a verification boundary only when the next phase starts.
        self.progress.update({'phase': step, 'percent': percent})

    def staged(self):
        if self.progress:
            self.progress.update({
                'phase': 'pair', 'percent': 100,
                'completed': ['queued', 'inspect', 'core_write', 'core_verify',
                              'application_download', 'application_verify', 'pair'],
            })

    def failed(self):
        if self.progress:
            self.progress['failed'] = True

    def reporter(self, callback):
        async def report(phase, completed, total):
            self.record(phase, completed, total)
            if callback:
                await callback(phase, completed, total)
        return report

    def snapshot(self, application, firmware, universal):
        app = application.update_status()
        core = firmware.update_status()
        pair = universal.update_status()
        value = dict(self.progress)
        value['completed'] = list(value.get('completed', ()))
        if pair.get('status') in ('ready', 'activating'):
            if int(pair.get('release_sequence', 0)) != value.get('release_sequence'):
                value = {'release_sequence': int(pair.get('release_sequence', 0)),
                         'type': 'universal', 'phase': 'pair', 'percent': 100}
            value['completed'] = ['queued', 'inspect', 'core_write', 'core_verify',
                                  'application_download', 'application_verify', 'pair']
        value.update({
            'application_status': app.get('status', 'idle'),
            'firmware_status': core.get('status', 'idle'),
            'universal_status': pair.get('status', 'idle'),
            'confirmation_phase': str(pair.get('confirmation_phase', ''))[:40],
        })
        if any(value.get(name) in ('trial', 'activating', 'committing') for name in (
                'application_status', 'firmware_status', 'universal_status')):
            value['phase'] = 'install'
        return value


telemetry = UpdateTelemetry()
