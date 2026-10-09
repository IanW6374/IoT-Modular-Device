# IoT-MD 3.0.0-alpha.111

This Alpha testing release fixes certificate layout and upgrade controls.

## Changes

- All certificate workspaces share a 48 rem maximum width and shrink on narrow
  screens. Certificate cards are stacked consistently rather than four across.
- Restart and install has a status-only circle, not a percentage. Measurable
  transfer and verification milestones retain percentages and completion ticks.
- Discard remains on the left and the primary update action on the right during
  manual selection, automatic staging and the staged-install view. Reconnected
  update tasks use the same milestone behaviour and control order.

## Install and test

Back up configuration, then install `universal-3.0.0-alpha.111.iotuni` through
the device's Update page or Management. The universal bundle contains matching
signed core and application components and uses firmware-first paired activation.
Do not factory-flash an already secured board.

Check all four certificate pages on desktop and a narrow viewport. Stage manual
application, core and universal files, and an automatic release. Verify the final
Restart and install circle has no percentage and the primary button remains to
the right of Discard when staging completes. Verify a reconnectable update task
preserves the same behaviour.

Runtime generation 207; signed release sequence 2816; core API 15 / native ABI 7.
The coordinated Alpha 110 HTTPS identity requirements still apply. This release
does not address IoT-MD-002's encrypted transactional-storage-full condition.

Host and offline DOM tests do not establish live-device or rendered-browser
qualification. Factory images, setup passwords and signing keys are not public
release assets.
