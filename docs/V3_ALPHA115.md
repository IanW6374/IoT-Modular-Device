# IoT-MD 3.0.0-alpha.115

Signed universal **test release** for the Management 3.2.4 action progress view.
There are no functional runtime changes from Alpha 114. Version metadata,
runtime generation and signed sequence advance to make this a real newer
upgrade, accepted by devices already running Alpha 114.

## Test on real devices

Back up configuration. Import the release into Management and create a universal
deployment using `universal-3.0.0-alpha.115.iotuni`. Select your devices, then stage
or install using the normal controls. This writes both signed components and
restarts the device when installation is requested; it is not a simulation.

Check the batch outcome summary, visible running counts at each milestone and
the searchable per-device stage table. Try stage and outcome filters, expand a
device's detail, and confirm filters remain selected during automatic refresh.
Completed devices should report Alpha 115 for both core and application.
Cancellation remains unavailable once installation is underway.

The update preserves configuration and existing hardware security. This release
does not install itself or change connected devices without an explicit update.
Alpha 114 fixes, including shared portal polling and Alpha 113 transaction
snapshot retention, remain included.

Runtime generation 211; signed release sequence 2820; core API 15 / native ABI 7.
Public assets are application, signed core, universal bundle, SBOM and provenance.
Factory images, setup passwords and signing keys are not public assets.
