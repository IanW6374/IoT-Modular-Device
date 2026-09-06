# IoT-MD v3.0.0-alpha.10 test note

## Purpose

Alpha 10 connects the remaining greenfield mechanisms into one deliberately
fail-closed integration candidate. The principal change is native platform ABI
6: an encrypted journal now binds a universal release's platform partition and
MicroPython runtime slot so the pair cannot be confirmed independently.

This release does not claim that any hardware-in-the-loop gate passed. The
proven compatibility runtime remains the default owner and active-v3 selection
continues to be refused until the release-bound qualification ledger is
complete.

## Included

- Native paired-release phases: prepared, trial, rollback, confirmed and
  rolled-back, stored in encrypted NVS with the release sequence and pair ID.
- Frozen-supervisor reconciliation before replaceable product startup.
- Runtime-first health confirmation followed by guarded native OTA
  confirmation; rollback records intent before restoring the previous runtime.
- Existing independent frozen recovery and bounded native job/event mechanisms.
- Existing native GPIO, ADC, UART, I2C and SPI lifecycle management.
- A production v3 composition root for transport, identity, fleet, migration,
  driver and cutover services.
- Side-effect-free shadow validation which cannot open listeners, publish MQTT
  state or claim hardware.
- Generation-safe opaque migration staging and a complete mapping of all 13
  supported v2 module variants into v3 physical-resource declarations.
- Portal qualification output which distinguishes implementation presence from
  observed production qualification.

## Expected behavior

The installed product should continue to behave like Alpha 9 because
compatibility mode remains the default. Maintenance > Release qualification
should report platform ABI 6, show a paired journal snapshot, and list all nine
greenfield mechanisms as implemented. Their qualification state remains false
until the corresponding signed HIL observations are recorded.

A universal trial must not become confirmed unless the expected platform
partition is running and the expected runtime slot has reached the startup
health gate. A mismatch or startup failure must restore the previous runtime
selection and request native rollback. Interrupted transitions must remain
visible in the paired journal for the frozen supervisor to reconcile.

## Required qualification

1. Interrupt power at every prepare, stage, trial, confirmation and rollback
   boundary and verify that no mixed pair becomes confirmed.
2. Corrupt or remove the replaceable runtime and exercise watchdog-loop and
   failed-trial recovery without importing the product application.
3. Saturate the native job/event queues and verify bounded, retryable errors.
4. Exercise resource conflict, shared-bus, interrupt cleanup and recovery tests
   across every physical backend and all 13 module variants.
5. Compare Wi-Fi, MQTT/Home Assistant, HTTPS, mTLS API and syslog behavior in
   shadow campaigns, including network loss and reconnect.
6. Exercise every managed enrollment/renewal method, trust replacement/removal,
   Management Suite policy/report exchange and representative v2 migrations.
7. Only after all evidence passes, test explicit shadow and active cutover plus
   permanent compatibility fallback after a failed active boot.

## Safety and rollback

The release sequence is `2715`. Install
`universal-3.0.0-alpha.10.iotuni`; application-only installation cannot provide
ABI 6. Do not manually change native qualification booleans or infer a passing
gate from successful installation alone.
