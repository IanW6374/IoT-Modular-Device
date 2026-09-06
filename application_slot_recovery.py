"""Narrow reporting and rollback operations for application trial slots."""


def executing_version(application, fallback=''):
    """Return the version actually executing, including an uncommitted trial."""
    state = application.update_status()
    if state.get('status') in ('trial', 'committing'):
        target = str(state.get('target_slot', ''))
        version = str(state.get('version', ''))
        if (target in application.SLOT_NAMES and version and
                application._file_exists(application._slot_path(
                    target, application.APPLICATION_ENTRY))):
            return version
    return application.running_version(fallback)


def restore_paired_slot(application, slot, failed_sequence=0):
    """Restore the recorded slot after an already-committed paired app fails."""
    if slot not in application.SLOT_NAMES:
        raise ValueError('paired rollback application slot is invalid')
    slots = application.slot_status()
    if not application.validate_slot_integrity(slot):
        raise ValueError('paired rollback application slot is unavailable')
    active = str(slots.get('active', ''))
    sequences = slots.get('sequences', {})
    failed_sequence = int(failed_sequence or 0)
    if active == slot:
        return False
    if failed_sequence and int(sequences.get(active, 0) or 0) != failed_sequence:
        raise ValueError('active application does not match paired release')
    application._write_json_atomic(application.SLOT_STATE_PATH, {
        'active': slot, 'versions': slots.get('versions', {}),
        'sequences': sequences,
    })
    version = str(slots.get('versions', {}).get(slot, ''))
    sequence = int(sequences.get(slot, 0) or 0)
    if version:
        application._write_text_atomic(application.VERSION_PATH, version)
    if sequence:
        application._write_text_atomic(application.RELEASE_SEQUENCE_PATH, str(sequence))
    application._remove_if_exists(application.STATE_PATH)
    application._remove_if_exists(application.BUNDLE_PATH)
    application.update_support.record_update_event(
        'application', 'paired_rollback', version,
        detail='restored slot ' + slot + ' after paired core rollback'
    )
    return True
