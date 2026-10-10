# IoT-MD 3.0.0-alpha.112

This Alpha testing release adds safe staging cancellation and consistent portal
warning/error handling. Use it with IoT MD Management Suite 3.2.0.

## Changes

- Cancel an update while staging from the device portal or Management. Pending
  activation commands are revoked, and cleanup waits for an active writer to
  stop safely. Cancellation is refused after installation/trial has started.
- Record intentional cancellation separately from failed updates. Management
  reconciles uncertain acknowledgements without replaying device mutations.
- Use red for rejected/failed operations, amber for incomplete work or interrupted
  reads, blue for accepted work, and green only for confirmed success.
- Display incomplete-update warnings above the action controls. Failed saves
  preserve unsaved values, including explicit rejection responses with HTTP 200.
- Surface interrupted overview, logs, diagnostics, task and update-status reads
  instead of silently showing old values as live. Retain completed milestones.

## Install and test

Back up configuration, then install `universal-3.0.0-alpha.112.iotuni` through
the device Update page or Management. It contains matching signed core and
application components with firmware-first paired activation. Do not factory-flash
an already secured device.

After upgrading, start another staging operation to test cancellation before
installation. Check that cancellation is acknowledged before another update can
start. Verify that rejected saves remain red and retain edited values, partial
update warnings span the workspace above the buttons, and interrupted reads show
amber until a successful refresh. Check Management Devices/List automatic refresh
while an unrelated deployment or backup is queued.

Runtime generation 208; signed release sequence 2817; core API 15 / native ABI 7.
The coordinated Alpha 110 shared HTTPS identity requirements still apply.
This release does not repair an already-full encrypted transactional store or
claim to resolve the underlying intermittent device connectivity fault.

Host and offline DOM tests do not establish live-device qualification. Factory
images, setup passwords and signing keys are not public release assets.
