"""Native-owned journal for paired platform/runtime activation.

The ESP-IDF side owns the durable decision.  The replaceable runtime only
performs filesystem slot changes requested by that journal and can therefore
reconcile safely after power loss at any boundary.
"""


class NativePairError(RuntimeError):
    pass


def _adapter(value):
    for operation in ('current_slot', 'activate', 'restore'):
        if not callable(getattr(value, operation, None)):
            raise NativePairError('runtime slot adapter is incomplete')
    return value


class NativePairCoordinator:
    def __init__(self, platform, runtime_slots):
        if not platform.capabilities()['updates']['native_pair_journal']:
            raise NativePairError('native paired-update journal is unavailable')
        self._platform = platform
        self._runtime = _adapter(runtime_slots)

    def prepare(self, pair_id, sequence, platform_label, runtime_slot):
        current = str(self._runtime.current_slot())
        return self._platform.prepare_pair(
            pair_id, sequence, platform_label, runtime_slot, current
        )

    def begin_trial(self, pair_id, runtime_slot):
        self._runtime.activate(runtime_slot)
        try:
            return self._platform.begin_pair_trial(pair_id, runtime_slot)
        except Exception:
            self._runtime.restore()
            raise

    def confirm(self, pair_id):
        state = self._platform.pair_snapshot()
        if state['phase'] != 'trial' or state['pair_id'] != pair_id:
            raise NativePairError('paired trial is not active')
        current = str(self._runtime.current_slot())
        if current != state['runtime_slot']:
            raise NativePairError('running runtime slot does not match journal')
        self._platform.mark_pair_runtime_healthy(pair_id, current)
        return self._platform.confirm_pair(pair_id)

    def rollback(self, pair_id, reason):
        state = self._platform.request_pair_rollback(pair_id, reason)
        restored = str(self._runtime.restore())
        if restored != state['previous_runtime_slot']:
            raise NativePairError('restored runtime slot does not match journal')
        return self._platform.complete_pair_rollback(pair_id, restored)

    def reconcile(self):
        """Return an explicit boot action; never infer successful health."""
        state = self._platform.pair_snapshot()
        current = str(self._runtime.current_slot())
        if state['phase'] == 'trial' and current != state['runtime_slot']:
            self._platform.request_pair_rollback(
                state['pair_id'], 'runtime slot changed during paired trial'
            )
            return {'action': 'rollback', 'state': self._platform.pair_snapshot()}
        if state['phase'] == 'rollback':
            restored = str(self._runtime.restore())
            if restored != state['previous_runtime_slot']:
                raise NativePairError('runtime rollback reconciliation failed')
            self._platform.complete_pair_rollback(state['pair_id'], restored)
            return {'action': 'rollback-complete', 'state': state}
        return {'action': 'none', 'state': state}

    def snapshot(self):
        return self._platform.pair_snapshot()
