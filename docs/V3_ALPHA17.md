# IoT-MD v3.0.0-alpha.17

Alpha 17 is a corrective qualification release. It adds no new greenfield
architecture mechanism and retains native platform ABI 6.

## Changes

- The manual-upgrade progress area shows one prominent current task without a
  duplicate numerical step count.
- Application, core and universal releases keep their file-specific vertical
  workflow after staging. Universal releases retain all eight stages through
  activation and reboot.
- File-type guidance is shown before selection and hidden once a file is
  selected, keeping the filename clear.
- Alpha is a supported automatic-upgrade channel across IoT-MD configuration,
  signed catalog validation and publishing.
- IoT MD Management Suite 2.2.3 can assign a verified release to Alpha and
  serves its signed catalog at `/alpha/latest.json`.

## Architecture status

All planned greenfield implementation mechanisms remain present. Promotion is
still blocked on release-bound hardware qualification, shadow parity and
controlled cutover evidence. The compatibility path remains intentionally
available as rollback and recovery protection until those gates pass.
