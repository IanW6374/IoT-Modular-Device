# IoT-MD 3.0.0-alpha.118

Functional universal test release for the live-progress redesign in Management
3.2.9. The new authenticated `/api/v3/fleet/update-status` endpoint returns the
small update/reconciliation projection instead of collecting broad inventory.
It requires `fleet:read`, exposes no credentials or signing material, and does
not mutate the device. Discovery advertises the `live_update_status` capability.

## Test with Management 3.2.9

Back up configuration, update Management to 3.2.9, and import this release.
Existing API v3 devices use inventory while receiving the enabling upgrade;
discovery, status and final health confirmation now have independent budgets.
API v2 remains retired. Select the signed
`universal-3.0.0-alpha.118.iotuni` for the normal staging/installation workflow.
It writes both components and restarts devices only when installation is
requested. Publishing the release does not install anything automatically.

Verify independent stage observations for all selected devices, proportional
rings, preserved table filters and informative stale/retrying hints. Inspect
Management's cached `/api/scheduler` for queue age, next retry, workflow stage,
request bytes and reservation/context/connect-headers/body timing. A temporarily
busy device must not stall other devices or make an ambiguous mutation replay.

After restart both application and core must report Alpha 118. A matching
sequence, matching dispatched-command evidence and fresh health response are
required for completion; an active trial or cached health is not sufficient.
Capability discovery is refreshed after installation so subsequent deployments
use the dedicated small endpoint. Reinstalling this same release must be
rejected as not newer. Cancellation still cannot undo installation once begun.

Management's handler limit remains configurable from 2 to 32 (default 8), with
half reserved for live progress. Status-read budget defaults to five seconds;
discovery and final confirmation use separate request-timeout budgets. Round
cadence depends on fleet size, latency and available workers. Offline scaled
3/50/100-device tests are not physical network/flash benchmarks: qualify a real
upgrade with passive capture started before deployment and scheduler evidence.

Runtime generation 214; signed release sequence 2823; core API 15 / native ABI 7.
Public artifacts are application, signed core, universal bundle, SBOM and source
provenance. Factory images, setup passwords and private signing keys are not
published. Configuration and existing hardware security are preserved.
