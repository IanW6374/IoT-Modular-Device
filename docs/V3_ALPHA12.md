# IoT-MD v3.0.0-alpha.12 test note

## Purpose

Alpha 12 repairs the paired-confirmation failure observed while installing
Alpha 11. Alpha 11 reached application health, but its core remained pending
verification and the ESP bootloader returned to Alpha 9. Because Alpha 11 had
already committed its application pointer, the older core could not load the
new frozen `application_slot_recovery` module and entered recovery.
The native trial was not prepared because the frozen coordinator attempted to
import its adapter from the application slot before that slot had been added to
the module path. Confirmation consequently had no matching native pair.

## Included

- Native core confirmation now precedes the durable application-slot commit.
- A failed or interrupted native confirmation leaves the old application slot
  selected; frozen recovery can discard the new trial without importing it.
- Native pair preparation uses a frozen direct ABI adapter and no longer
  depends on an application-slot module before that slot is on `sys.path`.
- Confirmation phases and exact errors are persisted in update history.
- A newer release can safely supersede a stale native pair journal.
- Trial-aware application version reporting no longer imports a helper that
  exists only in the new core.

## Expected behavior

Install `universal-3.0.0-alpha.12.iotuni` from the recovered Alpha 10
application/Alpha 9 core pair. The overview may report Alpha 12 as the executing
application during trial, but the durable application pointer remains Alpha 10
until the Alpha 12 core is valid. The terminal result must be either the complete
Alpha 12 pair or the complete previous pair, never a mixed pair.

## Safety and rollback

The release sequence is `2717`. If native confirmation fails, the update
history records `confirmation_failed` with the last completed boundary before
the device rolls both components back. Do not promote active v3 or mark paired
updates qualified from one successful installation; complete the associated
power-interruption matrix first.
