# IoT-MD v3.0.0-alpha.16

Alpha 16 is a corrective qualification release. It adds no new greenfield
architecture mechanism and retains native platform ABI 6.

## Changes

- Compact release packages explicitly import the Grove AC Voltage calibration
  transport in the generated live-route module.
- Unexpected authenticated request failures render a normal portal page with
  **Go back** and **Open device log** actions; exception detail remains in the
  device log.
- Rejected manual upgrade files stop the working state, reopen file selection,
  clear the rejected file and disable actions until another file is selected.
- Manual artifact guidance explains that universal files are for routine
  upgrades and component files are for recovery.
- Linked overview metrics retain plain text while hover and keyboard focus are
  indicated by the tile outline, elevation and focus ring.

## Architecture status

All planned greenfield implementation mechanisms remain present. Promotion is
still blocked on release-bound hardware qualification, shadow parity and
controlled cutover evidence. The compatibility path remains intentionally
available as rollback and recovery protection until those gates pass.
