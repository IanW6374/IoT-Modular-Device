# IoT-MD v3.0.0-alpha.30

Alpha 30 hardens encrypted storage and portal recovery after a power cycle. It
retains native platform ABI 6 and uses release sequence 2735.

## Power-cycle and storage resilience

Qualification snapshots are now read-only. Gate transitions persist their
derived history separately, but a full history sidecar no longer prevents live
qualification status or the portal from rendering. Under pressure, the recorder
keeps its authoritative counters and discards the oldest optional release
summaries first.

Both native transactional documents and the encrypted device configuration now
erase only their inactive alternating slot before allocating its replacement.
The active valid generation remains recoverable if power is interrupted during
the erase, write or commit transition, while NVS no longer needs temporary room
for an additional stale value.

## Portal refinements

The Maintenance menu now exposes **Upgrade** as the single entry into upgrade
selection; the transient installation page remains available only after a
release is selected. Automatic upgrade actions are right-aligned consistently.
The protected sole-administrator explanation is available as hover and
accessible help on the controls rather than occupying permanent form space.

Future portal request failures include the HTTP method and route in the device
log, making a recurrence traceable without exposing request data.

