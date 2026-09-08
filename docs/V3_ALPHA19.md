# IoT-MD v3.0.0-alpha.19

Alpha 19 closes the gap between a successful physical power-cycle test and the
release-bound qualification ledger. It adds no new greenfield architecture
mechanism and retains native platform ABI 6.

## Changes

- Retain the preceding durable boot snapshot transiently when a new boot
  begins, without changing the durable boot-state schema.
- Automatically record one successful power recovery when a `pwron_reset`
  follows a healthy boot and the new boot reaches healthy `running`.
- Exclude first boots, software resets, incomplete boots, degraded starts and
  repeated observations from power-recovery evidence.
- Emit `power_recovery_qualified` in persistent health history and present the
  power-recovery gate as device-observed evidence.
- Document that the pre-NTP and post-NTP event groups can belong to one boot;
  the authoritative indication of another restart is another `boot` event.

## Architecture status

All planned greenfield implementation mechanisms remain present. Promotion is
still blocked on complete release-bound hardware qualification, shadow parity
and controlled cutover evidence. The compatibility path remains available as
rollback and recovery protection until those gates pass.
