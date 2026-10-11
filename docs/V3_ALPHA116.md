# IoT-MD 3.0.0-alpha.116

Restores a responsive, equal-width certificate card grid. Certificate pages use
the available browser width instead of a permanently narrow single column.
Desktop and mobile layout checks cover one through four columns with no page
overflow.

## Testing with Management 3.2.5

Back up configuration, import this release into Management, and create a
universal deployment using `universal-3.0.0-alpha.116.iotuni`. This is a signed
newer release for devices on Alpha 115; it writes both components and restarts
the device when installation is requested.

Check the consistent milestone rings: grey for not running, amber for active,
red for failed and green for complete. Counts remain inside the rings and in
hover text, without extra completion/running label rows. The searchable device
table retains measured stage progress and per-device outcomes.

Management 3.2.5 separates action dispatch from four bounded polling workers and
publishes observed update progress before slower configuration/health/event
reads. Completion still requires the full confirmation path. Test that a slow
or restarting device does not freeze the remaining devices' status updates.
These polling changes need qualification on real devices.

Completed devices should report Alpha 116 for both core and application.
Cancellation is unavailable once installation begins. Configuration and
hardware security are preserved; no devices are installed automatically.

Runtime generation 212; signed release sequence 2821; core API 15 / native ABI 7.
Public assets include the application, signed core, universal bundle, SBOM and
provenance. Factory images, setup passwords and signing keys remain private.
