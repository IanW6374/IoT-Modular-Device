# IoT-MD v3.0.0-alpha.20

Alpha 20 fixes qualification evidence that could never accumulate across
upgrades and completes the pending portal account, certificate and presentation
changes. It retains native platform ABI 6.

## Qualification and recovery

- Release-local soak, health, storage, network and canary observations start
  fresh for each signed release.
- Paired-upgrade confirmations, successful managed renewals, physical power
  recovery and controlled platform validations persist in an independent ABI 6
  campaign ledger.
- An expected rollback remains visible as a diagnostic but does not itself fail
  the paired-upgrade gate; a genuine failed update still does.
- MQTT startup failure degrades the external service and starts bounded
  background reconnection rather than latching the whole device failed.
- A degraded external-service start now closes the boot transaction as locally
  healthy, preserving valid physical power-recovery evidence.

## Portal and identity

- Portal accounts have individual failed-attempt limits, persistent lockout,
  administrator unlock, inactive-session timeout and optional forced password
  replacement at next sign-in.
- Expired sessions return to a signed-out page instead of leaving stale content
  visible.
- **Renew now** runs the active managed certificate method in the background;
  manual packages continue to require an explicit replacement package.
- Certificate distinguished names use deterministic escaping across all views.
- Existing users and the new-user form share one fixed-width card grid.
- The Status menu includes a compact overall device-state LED: green for
  running, amber for transitional/degraded and red for failed/safe states.

## Architecture status

All planned greenfield implementation mechanisms remain present. Promotion is
still blocked on completion of the hardware qualification campaign, shadow
parity and controlled cutover evidence. Compatibility remains the protected
rollback path until those gates pass.
