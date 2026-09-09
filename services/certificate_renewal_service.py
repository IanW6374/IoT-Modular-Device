"""Application orchestration for immediate managed-certificate renewal."""


class CertificateRenewalService:
    def __init__(self, config, paths, renew, qualification, health,
                 reload_portal, reload_identities, task_start, task_status):
        self.config = config
        self.paths = dict(paths)
        self.renew = renew
        self.qualification = qualification
        self.health = health
        self.reload_portal = reload_portal
        self.reload_identities = reload_identities
        self.task_start = task_start
        self.task_status = task_status

    async def run(self):
        def progress(message):
            self.task_status['certificate-renewal'] = {
                'phase': 'running', 'message': str(message)
            }
        try:
            state = await self.renew(self.config, self.paths, progress)
        except Exception:
            self.qualification(False)
            raise
        self.qualification(True)
        self.health.record_event(
            'certificate_renewed', 'Managed certificate renewal completed',
            {'mode': self.config.get('mode', '')}, force=True
        )
        (self.reload_identities if self.config.get('mode') == 'iot_ca'
         else self.reload_portal)()
        expiry = ''
        if isinstance(state, dict):
            expiry = state.get('portal_not_after') or state.get('not_after') or ''
        return 'Certificate renewal completed' + (
            ' until ' + str(expiry) if expiry else ''
        )

    def request(self):
        mode = str(self.config.get('mode', 'manual'))
        if mode not in ('acme', 'iot_ca', 'self_signed'):
            raise ValueError(
                'The current manual certificate method cannot renew automatically'
            )
        if self.operation().get('phase') == 'running':
            raise ValueError('Certificate renewal is already running')
        return self.task_start(
            'certificate-renewal', self.run(),
            'Starting ' + mode.replace('_', ' ') + ' certificate renewal'
        )

    def operation(self):
        return dict(self.task_status.get('certificate-renewal', {}))
