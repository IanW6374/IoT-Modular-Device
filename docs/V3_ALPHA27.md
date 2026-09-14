# IoT-MD v3.0.0-alpha.27

Alpha 27 repairs qualification persistence and separates the upgrade portal
into focused workflows. It retains native platform ABI 6 and uses release
sequence 2732.

## Qualification storage

ESP-IDF error `4357` is `ESP_ERR_NVS_NOT_ENOUGH_SPACE`. The qualification
recorder alternates two transactional snapshots so an interrupted write never
destroys its latest committed evidence. Alpha 27 now erases only the stale
target snapshot when NVS cannot allocate its replacement, commits that reclaim
and retries the write. The opposite snapshot remains the recoverable current
generation throughout the transaction.

If storage still cannot accept the snapshot, the application reports
**encrypted transactional storage is full** instead of exposing the numeric
ESP-IDF error.

## Administrator safety

The only enabled administrator cannot be disabled or changed to a lesser role.
The portal visibly locks those two controls and explains how to unlock them by
enabling another administrator. The existing server-side rule remains the
authoritative protection against modified or crafted requests.

## Upgrade portal

Maintenance now contains an **Upgrades** submenu with three pages:

- **Available upgrades** checks the signed channel or accepts a local signed
  application, core or universal file.
- **Install upgrade** reviews and activates the currently staged release.
- **Settings** configures the channel, schedule, automatic download and
  automatic activation policy.

Automatic downloads and local uploads both finish on **Install upgrade**.
Discarding a staged release returns to **Available upgrades**.

Install `universal-3.0.0-alpha.27.iotuni`; an application-only update cannot
install the native NVS repair.
