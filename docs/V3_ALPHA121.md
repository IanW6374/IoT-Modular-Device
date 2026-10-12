# IoT-MD 3.0.0-alpha.121

Functional testing release for the update-status freezes observed on Alpha 120,
paired with Management 3.2.11. Synchronous Python P-256 verification is replaced
in the frozen core by strict SDK Mbed TLS verification. Signature format, low-S
checks, trust anchors, authorization and anti-replay protections are unchanged.
The device fails closed if the native verifier is missing. Bounded, secret-free
UART duration reports support physical timing qualification.

API v3 now identifies confirmed operation-reservation failures before dispatch.
Management 3.2.11 can fail these new jobs instead of leaving them checking.
Ambiguous or post-dispatch failures remain uncertain and are not replayed.
Existing uncertain jobs are not rewritten retroactively. A partially committed
reservation may still consume its key even though no command was dispatched.

## Controlled test

Back up configuration and install Management 3.2.11. Upgrade both core and
application using `universal-3.0.0-alpha.121.iotuni`; an application-only update
does not install the native verifier. The upgrade receiving Alpha 121 still
starts under the old core, so its timing alone cannot qualify the new verifier.
After installation, correlate separately approved receive-only UART captures
with downloaded deployment diagnostics during a subsequent newer release.

Confirm that signatures remain strictly checked, progress reads stay responsive,
and completion still requires matching command/release evidence, no active
trial and fresh health. Reinstalling Alpha 121 must be rejected as not newer.
No timeout, retry, cancellation or device-handler settings are changed.

Read-only NVS allocation counters are added to transport diagnostics and
confirmed storage-rejection responses. This release does not resize storage,
erase credentials or reclaim current records. Latest-only documents and NVS
headroom can still exhaust the existing partition; 002's exact allocation and
the remedy still require investigation. Devices unable to stage an update may
need a separately approved recovery/bootstrap procedure.

Runtime generation 217; signed release sequence 2826; core API 15 / native ABI
7. Only application, signed core, universal, SBOM and provenance are public.
Factory images, setup passwords and signing keys remain private. Publication
does not install firmware, reset devices or clean their storage.
