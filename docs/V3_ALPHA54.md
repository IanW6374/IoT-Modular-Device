# IoT-MD v3.0.0-alpha.54

Release sequence: 2759. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 54 repairs the upgrade discard-and-retry path. Discard now clears the
resumable artifact, any sequential universal-upload plan, every verified but
inactive component and the automatic-release orchestration record. Cleanup
always visits every layer even when an earlier layer reports success.

When Discard is selected during background verification, the request is bound
to that upload identifier. Verification stops at its next progress checkpoint,
then performs the same complete cleanup before another release is staged. This
prevents the abandoned task from making a later workflow reach a disabled
**Restart and install** step and then return to release selection.

Alpha 54 retains Alpha 53's in-place API scope editor and is an application-only
signed release compatible with the Alpha 52 native core (ABI 6).
