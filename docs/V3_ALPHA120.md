# IoT-MD 3.0.0-alpha.120

Signed, version-only universal test release; no functional changes from Alpha
119. It provides a genuine newer paired upgrade for testing Management 3.2.10's
retained per-request timing diagnostics. It is not a fix for the observed
physical-device telemetry freezes, whose transport cause is not yet established.

## Controlled test

Back up configuration and install Management 3.2.10. Devices should have Alpha
119 in both core and application. Start separately approved receive-only USB
captures before dispatch, then select `universal-3.0.0-alpha.120.iotuni` in
Management. This performs real flash writes and restarts; release publication
does neither.

Download the deployment's progress diagnostics from Actions or Logs / Activity,
including after completion. Retained failures must remain visible in the JSON
after successful reads. Correlate UTC epoch timestamps and read offsets with
USB logs to distinguish reservation, TLS/connect/headers, body, decoding and
health-confirmation failures. Connect/headers includes TLS establishment, not
a separately measured handshake. Share the export if progress stalls or jumps.

Completion still requires matching command/release evidence, no active trial,
and fresh health. Reinstalling Alpha 120 must be rejected as not newer. This
release does not change timeout settings, authorization, anti-replay protection,
configuration or drivers.

Runtime generation 216; signed release sequence 2825; core API 15 / native ABI
7. Public artifacts are application, signed core, universal, SBOM and source
provenance. Factory images, setup passwords and signing keys remain private.
