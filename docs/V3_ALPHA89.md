# IoT-MD v3.0.0-alpha.89

Release sequence: 2794. Native ABI: 6. Required runtime core API: 12.

Alpha 89 lets an enrolled Management Suite create and restore the device's
existing complete encrypted backup through the configuration API. The backup
contains operational credentials and secrets, module configuration,
certificates, private keys, API trust and fleet state. Encryption and
authentication happen on the device before the envelope crosses the mTLS API.

Restore keeps the existing two-step safety model: the target validates and
previews selected sections, returns a short-lived token, and applies only that
previewed token. Applying a restore records an audit event and requires a
restart. The Device API accepts the larger bounded request needed by a maximum
complete-backup envelope.
