# IoT-MD 3.0.0-alpha.122

Signed, version-only universal test release; no functional changes from Alpha
121. It provides a genuine newer paired upgrade so devices already running
Alpha 121's native signature verifier can exercise it during the entire update
workflow. It is not a new fix for device storage exhaustion or a claim that
physical update responsiveness has been qualified.

## Controlled test

Back up configuration and use Management 3.2.11. Confirm Alpha 121 is installed
in both core and application, then select `universal-3.0.0-alpha.122.iotuni`.
This performs real flash writes and restarts; publishing the release does not.
Any USB logging needs separate approval before opening ports.

Download the deployment's retained progress diagnostics, including after
completion. If approved UART captures are available, correlate UTC timestamps
with native P-256 duration reports and listener heartbeat diagnostics. Check
that status reads remain responsive through staging and fresh health
confirmation. Share the diagnostics if reads stall, time out or jump stages.

Completion still requires matching command/release evidence, no active trial
and fresh health. Reinstalling Alpha 122 must be rejected as not newer.
Configuration, authorization, signatures, anti-replay protection, timeout/retry
settings and drivers are unchanged from Alpha 121. Existing uncertain jobs are
not rewritten; devices with full storage may still reject staging.

Runtime generation 218; signed release sequence 2827; core API 15 / native ABI
7. Public files are application, signed core, universal, SBOM and provenance.
Factory images, setup passwords and signing keys remain private.
