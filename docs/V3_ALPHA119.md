# IoT-MD 3.0.0-alpha.119

Signed, version-only **universal test release**, with no functional changes from
Alpha 118. This is a real newer upgrade, not a browser simulation or same-version
reinstall. It exercises core/application staging, verification, restart and
health confirmation through Management 3.2.9's redesigned live progress path.

## Test procedure

Back up configuration and ensure Management 3.2.9 is installed. For the intended
test, devices should already have Alpha 118 in both application and core; that
enables the small authenticated live update-status endpoint for the entire
upgrade. Import this release and select
`universal-3.0.0-alpha.119.iotuni` in a normal multi-device deployment. Installing
it performs real flash writes and restarts devices. Publication alone does not
install it, and no hardware is changed during release preparation.

Check independent stage updates, proportional rings, retained table filters and
stale/retrying tooltips. Use Management's cached `/api/scheduler` to inspect
per-device request timing, queue age and retry behaviour. One slow or restarting
device must not stop observations for other devices. An ambiguous command must
be reconciled by reads rather than automatically replayed.

Successful devices must report Alpha 119 for both components and only become
complete after matching dispatched-command/release evidence, no active trial,
and fresh health confirmation. Reinstalling Alpha 119 should then be rejected
as not newer. Test cancellation while staging; it cannot undo an installation
which has already begun.

The handler limit remains configurable from 2 to 32, default 8, with half the
workers reserved for live progress. Physical network/flash behaviour must be
qualified on the actual devices; offline load tests are not network benchmarks.

Runtime generation 215; signed release sequence 2824; core API 15 / native ABI 7.
Configuration, credentials and hardware security are retained. Public assets
are application, signed core, universal bundle, SBOM and source provenance.
Factory images, setup passwords and private signing keys are not published.
