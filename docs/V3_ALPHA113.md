# IoT-MD 3.0.0-alpha.113

This Alpha testing release reduces redundant transaction snapshot occupancy in
the shared encrypted NVS store. Use it with IoT MD Management Suite 3.2.1.

## Changes

- Reclaim only strictly older, CRC-verified transaction snapshots in the bounded
  qualification and API-operation namespaces. Preserve the latest generation,
  credentials, network trials, paired-update records and API anti-replay
  watermarks. Do not create missing namespaces during reclamation.
- Verify each newly committed snapshot before retiring its predecessor. A failed
  write retains the previous generation; corrupt unrelated records are left
  untouched. A true capacity failure still fails rather than erasing user data.
- Management 3.2.1 places Cancel badges immediately before individual statuses
  and Cancel all before the overall status. Batch cancellation confirms once,
  submits sequentially, skips installation in progress and reports individual
  failures without automatically replaying unconfirmed mutations.

## Install on devices without the storage error

Back up configuration, then install `universal-3.0.0-alpha.113.iotuni` through
Management or the device's Maintenance / Update page. It contains matching signed
core and application components with firmware-first paired activation.

## Bootstrap IoT-MD-001 / 002 when Management cannot start the update

The Management mutation first reserves an API-operation journal record in NVS.
The device portal's manual signed core upload bypasses that journal: it writes
the inactive OTA partition and stores update state in the encrypted filesystem.
This provides a way to install the core fix before retrying API operations.

Work on one device at a time, keeping power connected throughout:

1. Open the device's HTTPS portal and Maintenance / Update / Manual. If a previous
   update is still active or partially staged, use its local Cancel / Discard
   control and wait for acknowledgement. Do not interrupt an installation/trial.
2. Select `iotmd-core-3.0.0-alpha.113.iotcore`, stage it, then use Restart and install.
   Do not select the universal bundle for this bootstrap step.
3. Wait for the portal to return and confirm that core Alpha 113 is installed.
   Verify storage headroom and a successful Management refresh before proceeding.
4. Install `application-3.0.0-alpha.113.iotapp` as an application-only update through
   the portal or Management. Confirm both core and application are Alpha 113.
   Do not retry the same universal bundle after separately installing its core:
   that core's signed sequence is already installed.
5. Repeat for the other affected device only after the first has been verified.

If manual core staging or the headroom check fails, stop and collect diagnostics
before choosing a separately approved secured-device UART recovery. Do not
factory-flash, erase NVS, reset configuration or replace signing keys.

## Validation and limits

Runtime generation 209; signed release sequence 2818; core API 15 / native ABI 7.
Existing Alpha 110/111 applications can run with this core during the two-step
bootstrap. The coordinated Alpha 110 shared HTTPS identity requirements apply.

Host tests compile the actual native retention helper and commit path against a
bounded NVS model, including write/readback failures, protected namespaces and
power-interruption boundaries. This is not physical power-cut qualification or
confirmation that the bootstrap has already been tested on the connected devices.
The fix does not expand NVS or claim to resolve intermittent connectivity faults.
Factory images, setup passwords and signing keys are not public release assets.
