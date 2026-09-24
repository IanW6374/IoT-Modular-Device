"""Application boundary for controlled qualification evidence and scenarios."""

import qualification_control


class QualificationControlService:
    def __init__(self, qualification, health, log_output, product_version,
                 watchdog_getter, recovery_request, reset_schedule):
        self.qualification = qualification
        self.health = health
        self.log_output = log_output
        self.product_version = str(product_version)
        self.watchdog_getter = watchdog_getter
        self.recovery_request = recovery_request
        self.reset_schedule = reset_schedule
        self.watchdog_starvation = False

    def should_feed_watchdog(self):
        return not self.watchdog_starvation

    def record(self, payload, actor):
        run_id = str(payload.get('run_id', '')).strip() if isinstance(payload, dict) else ''
        for previous in reversed(self.health.snapshot().get('events', ())):
            if previous.get('kind') != 'qualification_evidence':
                continue
            values = previous.get('values') or {}
            if values.get('run_id') != run_id:
                continue
            if (values.get('gate') != payload.get('gate') or
                    values.get('outcome') != payload.get('outcome')):
                raise ValueError('qualification run ID was already used')
            result = dict(values)
            result.update(duplicate=True, notes='', evidence_digest=(
                values.get('evidence_digest', '')
            ))
            return result
        event = qualification_control.controlled_event(
            payload, actor, self.qualification.record_validation
        )
        self.log_output(
            'Qualification', 'Evidence',
            {'log': (
                event['actor'] + ' recorded ' + event['outcome'] + ' for ' +
                event['gate'] + ' (' + event['run_id'] + ')'
            ), 'force': True, 'audit': True},
            'INFO' if event['outcome'] == 'success' else 'ERROR'
        )
        self.health.record_event(
            'qualification_evidence', 'Controlled qualification observation',
            {
                'gate': event['gate'], 'outcome': event['outcome'],
                'run_id': event['run_id'], 'actor': event['actor'],
                'evidence_digest': event['evidence_digest'],
            }, force=True,
            severity='info' if event['outcome'] == 'success' else 'error',
            component='qualification', correlation_id=event['run_id']
        )
        return event

    def scenario(self, payload, actor):
        request = qualification_control.scenario_request(
            payload, actor, self.product_version
        )
        if (request['scenario'] == 'watchdog-recovery' and
                self.watchdog_getter() is None):
            raise RuntimeError('watchdog is unavailable')
        self.log_output(
            'Qualification', 'Disruptive scenario',
            {'log': (
                request['actor'] + ' started ' + request['scenario'] +
                ' (' + request['run_id'] + ')'
            ), 'force': True, 'audit': True}, 'WARNING'
        )
        if request['scenario'] == 'watchdog-recovery':
            self.watchdog_starvation = True
        elif request['scenario'] == 'native-recovery':
            self.recovery_request(
                'controlled qualification ' + request['run_id']
            )
            self.reset_schedule('qualification_native_recovery', 1500)
        return request
