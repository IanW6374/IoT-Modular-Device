# IoT-MD v3.0.0-alpha.29

Alpha 29 unifies automatic and manual upgrade selection and installation. It
retains native platform ABI 6 and uses release sequence 2734.

## Unified operator workflow

The Available upgrades page now presents Summary, Upgrade already staged,
Rollback, Automatic upgrade and Manual upgrade in that order. Choosing either
an automatic release or a local signed file opens the same dedicated Install
upgrade page. That page derives its vertical steps from the selected release
type and does not download, upload, verify or stage anything until the operator
selects **Initiate upgrade**.

Automatic work remains inside the normal portal shell and returns to Install
upgrade when staging completes. Manual and automatic releases then share the
same staged state and **Restart and install** action instead of exposing two
partly independent upgrade interfaces.

## Constrained-device bridge

Alpha 29 includes Alpha 28's signed universal-plan storage repair. A device
running Alpha 26 or Alpha 27 may still be unable to receive that repair from a
large universal file. Install and activate
`application-3.0.0-alpha.29.iotapp` first, allow its trial to confirm, and then
install `universal-3.0.0-alpha.29.iotuni`.

A device already running Alpha 28 has the repaired uploader and can install
the Alpha 29 universal package directly. The application-first path remains a
safe alternative when available filesystem capacity is unusually low.

Standalone application and core bundles remain recovery artifacts and cannot
request universal-only storage reclamation.
