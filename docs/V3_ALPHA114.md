# IoT-MD 3.0.0-alpha.114

This Alpha testing release fixes shared task-status polling across authenticated
device portal pages. Management 3.2.3 can be used unchanged.

## Changes

- Keep one task-status request in flight per tab. Start the next periodic read
  three seconds after the previous read finishes, including its timeout.
- Coalesce refreshes requested while a read is pending; discard the superseded
  response so an older failure cannot recreate a warning after a fresh request.
- Pause background-tab polling and refresh on return. Stop polling on page exit
  and resume correctly when restored from the browser's back/forward cache.
- Keep genuine failed-read warnings and last known task data. Only valid,
  current responses clear the warning; failures are not disguised as success.

## Install and test

Back up configuration, then install `universal-3.0.0-alpha.114.iotuni` through
Management or Maintenance / Update on the device. Confirm core and application
both report Alpha 114, then reload any already-open portal tabs to load the new
JavaScript.

Leave API settings and other portal pages open, switch tabs and return, and
confirm the task indicator continues refreshing without overlapping task reads.
A genuine network interruption should still show an amber warning, retain the
last task data and clear the warning after connectivity returns.

Runtime generation 210; signed release sequence 2819; core API 15 / native ABI 7.
Offline browser tests reproduce slow reads and stale failures; they do not prove
that an underlying device transport or TLS fault is resolved. The Alpha 113 NVS
retention fix remains included. Devices still unable to start a Management update
because storage is full should follow the signed-core-first bootstrap described
in [Alpha 113](V3_ALPHA113.md), using the matching Alpha 114 core/application files.
Factory images, setup passwords and signing keys are not public release assets.
