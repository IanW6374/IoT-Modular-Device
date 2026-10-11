# IoT-MD 3.0.0-alpha.117

Signed universal **test release** for Management 3.2.7's configurable device
handlers and live-progress polling. There are no functional firmware changes
from Alpha 116. Version metadata, runtime generation and the signed release
sequence advance so this is accepted as a newer upgrade, not a same-version
reinstall or a browser simulation.

## Test on real devices

Back up configuration. Update Management to 3.2.7, import this release, and create
a universal deployment using `universal-3.0.0-alpha.117.iotuni`. Select devices
and stage or install through the normal controls. This writes both signed
components and restarts each device when installation is requested.

Verify that progress continues independently for other devices while one is
slow or restarting. Check proportional stage rings, per-device stage progress,
last-read age and stale/retrying hints. The searchable table should retain its
filters during dedicated progress refreshes. Installation should be confirmed
only after matching component versions and a fresh health response.

Management's **Maximum concurrent device handlers** defaults to 8 and can be
set from 2 to 32 in HA configuration; restart the add-on after changing it.
Half the capacity is reserved for live progress. Larger fleets still need
qualification on the actual HA host and network; simulated load tests are
not network benchmarks.

Completed devices should report Alpha 117 for both core and application.
Cancellation remains unavailable once installation begins. The update retains
Alpha 116 fixes, configuration and hardware security; no devices are installed
automatically. After installing Alpha 117, attempting it again should report
that no newer compatible release exists.

Runtime generation 213; signed release sequence 2822; core API 15 / native ABI 7.
Public assets include application, signed core, universal bundle, SBOM and
provenance. Factory images, setup passwords and signing keys remain private.
