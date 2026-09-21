# IoT-MD v3.0.0-alpha.35

Alpha35 uses release sequence 2740 and retains native platform ABI 6,
MicroPython 1.29.0 and ESP-IDF 5.5.5.

## Upgrade page

The Automatic method now contains a concise check-result badge, such as
**Upgrade available** or **Up to date**, instead of a separate last-check metric.
The redundant upgrade-status summary is removed. **Staged** remains a method
when a verified release is available: **Stage upgrade** prepares a release
without rebooting, and activation remains explicit.

Upgrade history is an always-visible subsection. Manual and scheduled release
checks are recorded with their outcome and available version. The latest 20
checks are persisted separately from the latest 20 upgrade events, so frequent
checks do not evict installation evidence. Earlier checks cannot be reconstructed.

## Retrying failed qualification tests

Later success does not clear every latched qualification failure. Administrators
can now expand **Restart failed test** on a failed gate, provide a reason and
confirm the retry. Only that gate's active evidence is reset; it must pass again.
Health and storage begin fresh observation windows. Other gates and the general
soak window are preserved. Canary health follows the active pause condition and
clears automatically when that condition resolves; it has no reset control.

Before clearing evidence, the recorder durably archives the previous failure,
administrator, reason, release and time. The bounded archive retains at most eight
retry records within a 4096-byte history budget shared with release summaries.
If archival storage fails, the gate remains blocked. A reset-write failure also
leaves the failed gate intact, though its retry request may already be archived.
Stale retry forms are rejected. State version 2 and history version 1 are migrated
without discarding existing qualification evidence.

Host and browser checks are not hardware qualification. Follow the
[Alpha35 device checks](qualification/v3.0.0-alpha.35.md) before promotion.
