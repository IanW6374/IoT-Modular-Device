# IoT-MD v3.0.0-alpha.13 test note

## Purpose

Alpha 13 repairs the forward-compatibility failure observed when Alpha 12 was
installed from the recovered Alpha 10 application/Alpha 9 core pair. The Alpha
9 frozen coordinator staged a valid signed universal transaction using its
older state format, which did not contain native `pair_id`, runtime-slot or
confirmation fields. After reboot, the Alpha 12 core rejected the empty pair
identifier and safely rolled both trial components back.

## Included

- Activating transactions created by a pre-ABI-6 coordinator are upgraded
  before native pair preparation.
- The pair identifier is deterministically derived from the signed release
  sequence.
- Trial and previous runtime slots are reconstructed from the application
  trial state and durable active slot.
- Missing confirmation fields are initialised and the migrated state is
  persisted before native calls.
- Update history records `pair_state_upgraded` for diagnostic evidence.
- Alpha 12's native-first commit ordering and power-loss protections remain.

## Expected behavior

Install `universal-3.0.0-alpha.13.iotuni` from the Alpha 10 application/Alpha 9
core pair. The history should record `pair_state_upgraded`, followed by the
normal confirmation phases. Both overview versions must finish on Alpha 13.

## Safety and rollback

The release sequence is `2718`. Invalid or incomplete legacy state still fails
closed before the application is loaded. A failed native preparation must
leave the device on the prior working pair.
