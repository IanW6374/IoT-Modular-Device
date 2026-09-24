"""Validate controlled qualification evidence and destructive test requests."""

CONTROLLED_GATES = (
    'native-recovery', 'watchdog-recovery',
    'identity-interoperability', 'fleet-interoperability',
    'migration-rollback', 'driver-hardware',
)

AUTOMATED_SCENARIOS = ('watchdog-recovery', 'native-recovery')


def _text(value, name, maximum, required=True):
    value = str(value or '').strip()
    if (required and not value) or len(value) > maximum:
        raise ValueError(name + ' is invalid')
    return value


def controlled_event(payload, actor, recorder):
    """Record one observed result; callers never set a gate status directly."""
    if not isinstance(payload, dict):
        raise ValueError('qualification evidence must be an object')
    gate = _text(payload.get('gate'), 'qualification gate', 48)
    if gate not in CONTROLLED_GATES:
        raise ValueError('qualification gate is not a controlled campaign gate')
    outcome = _text(payload.get('outcome'), 'qualification outcome', 16)
    if outcome not in ('success', 'failure'):
        raise ValueError('qualification outcome must be success or failure')
    run_id = _text(payload.get('run_id'), 'qualification run ID', 64)
    notes = _text(payload.get('notes'), 'qualification notes', 160, False)
    evidence_digest = _text(
        payload.get('evidence_digest'), 'qualification evidence digest', 96,
        False
    )
    if payload.get('confirm') not in (True, 'yes', 'true', 'confirmed'):
        raise ValueError('confirm that this is an observed qualification result')
    actor = _text(actor, 'qualification actor', 64)
    if recorder is None:
        raise RuntimeError('qualification recorder is unavailable')
    if not recorder(gate, outcome == 'success'):
        raise RuntimeError('qualification result could not be recorded')
    return {
        'gate': gate, 'outcome': outcome, 'run_id': run_id,
        'actor': actor, 'notes': notes, 'evidence_digest': evidence_digest,
    }


def scenario_request(payload, actor, product_version):
    """Validate a deliberately disruptive test request without executing it."""
    if not isinstance(payload, dict):
        raise ValueError('qualification scenario must be an object')
    scenario = _text(payload.get('scenario'), 'qualification scenario', 48)
    if scenario not in AUTOMATED_SCENARIOS:
        raise ValueError('qualification scenario is unavailable')
    run_id = _text(payload.get('run_id'), 'qualification run ID', 64)
    expected = 'execute ' + scenario
    if str(payload.get('confirmation', '')).strip().lower() != expected:
        raise ValueError('type "' + expected + '" to execute this scenario')
    if '-alpha.' not in str(product_version):
        raise RuntimeError('destructive qualification scenarios require an alpha build')
    return {
        'scenario': scenario, 'run_id': run_id,
        'actor': _text(actor, 'qualification actor', 64),
        'disruptive': True,
    }
