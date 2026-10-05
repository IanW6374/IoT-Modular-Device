# IoT-MD v3.0.0-alpha.99

Release sequence: 2804. Required core API: 13. Runtime generation: 196.

This universal update hardens TLS socket cleanup and accept-loop supervision.
It addresses verified code weaknesses observed while diagnosing IoT-MD-001's
TLS handshake stalls; it does not claim to prove the cause of the original
`EPERM` report. Existing certificate verification and API scopes are unchanged.
The unused ESP-NOW gateway binding is excluded to keep the signed, padded
core within the existing universal staging limit; normal Wi-Fi/MQTT remains.

Install the **universal** bundle to update the core and application together.
Its unpublished inner application permits staging on Core API 12; firmware
activates first and the paired trial confirms under Core API 13. The public
standalone application correctly rejects cores older than API 13.

Listeners recover after terminal accept-task failures without rebooting or
interrupting module/MQTT work. TLS errors carry stage, peer, exception/errno
and internal/DMA heap figures into syslog. These diagnostics intentionally do
not contain request bodies, query strings, secrets or certificate contents.

See [qualification checks](qualification/v3.0.0-alpha.99.md). Host tests and a
production firmware build are not substitutes for testing on the affected
devices.
