"""Start the renewal strategy owned by the selected certificate method."""

import certificate_manager
import iot_ca_enrollment
import setup_workflow


async def monitor(config, paths, log_output, reload_portal,
                  reload_identity_set, outcome=None):
    mode = str(config.get('mode', 'manual'))
    if mode == 'acme':
        await certificate_manager.renewal_monitor(
            config, paths['trust-ca'], log_output, reload_portal,
            outcome=outcome
        )
    elif mode == 'iot_ca':
        await iot_ca_enrollment.renewal_monitor(
            config, paths, setup_workflow._validate_certificates,
            log_output, reload_identity_set, outcome=outcome
        )
    elif mode == 'self_signed':
        await certificate_manager.self_signed_renewal_monitor(
            config, log_output, reload_portal, outcome=outcome
        )
    elif mode == 'manual':
        log_output(
            'Local', 'Manual certificate package',
            {'log': 'Automatic renewal is unavailable. Replace the public portal and '
                    'private Device API/fleet certificates before either identity expires.',
             'force': True},
            'INFO'
        )


async def renew_now(config, paths, progress=None):
    """Renew immediately using the active managed enrollment method."""
    mode = str(config.get('mode', 'manual'))
    report = progress if callable(progress) else None
    if mode == 'acme':
        return await certificate_manager.issue(
            config.get('directory_url', ''), config.get('hostname', ''),
            paths['trust-ca'], progress=report
        )
    if mode == 'iot_ca':
        return await iot_ca_enrollment.renew(
            config, paths, setup_workflow._validate_certificates, report
        )
    if mode == 'self_signed':
        if report:
            report('Generating a new self-signed device identity')
        return certificate_manager.install_self_signed(
            config.get('hostname', '')
        )
    raise ValueError(
        'Manual certificate packages cannot be renewed automatically'
    )
