# IoT-MD v3.0.0-alpha.83

Release sequence: 2788. Native ABI: 6. Required core API: 11.

Alpha 83 consolidates Device API client enrolment into one certificate type.
Administrators assign Standard, Management Suite, Qualification automation or
Custom permissions while uploading the certificate, and can continue editing
those scopes later without enrolling another copy of the same identity.

Configuration profiles also accept the complete automatic-update schedule and
separately structured Wi-Fi and MQTT secrets. Secrets are delivered only over
the mutually authenticated Device API and are written through the device's
existing encrypted credential store.

This is an application-only update and retains the Alpha 78 frozen core.
