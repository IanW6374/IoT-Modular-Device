# IoT-MD v3.0.0-alpha.80

Release sequence: 2785. Native ABI: 6. Required core API: 11.

Alpha 80 exposes the device's automatic-update schedule through the
authenticated configuration inventory. IoT-MD Management Suite 2.3.0 uses
that schedule for its default managed deployment: the update is staged as soon
as the deployment is created, then activated during the device's configured
daily or weekly slot.

This is an application-only release and retains the Alpha 78 frozen core.
Install Alpha 78 universal first when upgrading from an older core.
