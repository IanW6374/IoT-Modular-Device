# Device-owned update operation design

Status: API-based production source integration implemented in Alpha 123 and
Management 3.2.12 after explicit user approval. Host/offline tests cover admission,
worker ordering, cancellation, reboot recovery and exact-ID observation. No
connected device has been changed. Physical power-cut durability and API
responsiveness under real transfers remain testing gates. Optional MQTT is now
implemented in Alpha 124 / Management 3.2.13 after the user confirmed a configurable trusted
broker (`mqtt-broker.home.arpa`) and topic defaults. API remains the default.

## Authority and identity

One durable device operation spans release applicability, transfer, signature
verification, staging, activation and local health confirmation. Management
keeps the requested operation ID, desired release and latest verified observation.
Installed versions and connection freshness are independent observations, not
proof that this operation succeeded.

Admission keeps the existing format-2 signed policy, mTLS scopes,
generic API mutation reservation and protected anti-replay watermarks. Its first
signed command ID is a random 128-bit lowercase hexadecimal operation ID. A plan
contains exactly check/download[/activate], with one explicit release type and
sequence throughout. This avoids adding unsigned fields or changing native
signature canonicalisation. No automatic mutation replay is introduced.

Admission ordering is reserve API request -> verify signed policy and identity ->
reserve durable lifecycle as prepared -> commit executable policy -> commit
accepted lifecycle -> worker executes. Prepared operations cannot execute.
After a power loss, prepared admission is accepted only if the committed signed
policy matches every plan field; otherwise it becomes interrupted.

## Durable storage

`update_operations.py` reserves two 8-KiB slots on the encrypted VFS. The board's
`firmware/partitions-8MiB-ota.csv` marks the VFS encrypted. It retains one active
operation and up to three earlier terminal records. Capacity must be reserved
before effects. Alternating checksummed snapshots are flushed and read back;
corrupt state fails closed, rather than resetting replay permission.

Only lifecycle/stage boundaries are persisted. Percentage samples remain in RAM,
with boot ID and sample counter. This does not move, erase or reset existing
encrypted NVS credentials or API anti-replay watermarks. It also does NOT solve
existing NVS exhaustion for the generic API admission ledger; that remains a
separate release-readiness issue.

The checksummed dual slots are a host-tested design, not yet a hardware-proven
power-cut guarantee. FAT metadata behavior, flush support, allocation headroom,
flash wear and supervisor recovery must be qualified on the production board.

## Lifecycle

Prepared -> accepted -> checking -> staging -> staged -> installing -> complete.
Staged may wait as scheduled. Before installation, cancellation transitions to
cancelling and only becomes cancelled after the actual worker has stopped and
staged data has been discarded. Installation cannot be cancelled. Failed and
interrupted are explicit terminal records. Interrupted means unresolved to
Management, not successful cancellation or proof of update failure.

Activation intent must be flushed before calling existing native activation.
Completion is recorded only after local startup health and paired confirmation,
with the exact offered release sequence and idle component trial state. Versions
equal to or newer than the desired version cannot independently complete a job.
Reboot during checking/staging becomes interrupted; it never repeats effects.
Staged recovery must verify component readiness before allowing activation.

The production executor must be tested for cancellation concurrent with every
yield, policy save failure, activation response loss, partial pair confirmation,
post-confirmation journal failure, and booting a rolled-back application that
does not understand this contract. The existing generic API reservation remains
the admission watermark when older operation records age out.

## Observation and scaling

Authenticated snapshot route:
`GET /api/v3/fleet/update-operations/<operation-id>`, requiring fleet:read.
Discovery advertises `update_operation_contract: 1`. Management persists the ID
before sending admission and reads that exact operation thereafter. Missing
records, transport failures and stale data are not outcomes. New jobs require
the new firmware contract; there is no version-inference compatibility fallback.

`update_operation_contract.py` in Management validates device ID, operation ID,
policy sequence, exact release identity, bounded state, monotonic revision and
sample ordering. It does not accept credentials or arbitrary report fields.
It is connected to deployment polling and durable result persistence. Cohort
rollouts use the same queued per-device operation path. Existing retired/history
records are preserved; new dispatch does not fall back to inferred tracking.

Optional MQTT reporting is implemented in Alpha 124 / Management 3.2.13. Management creates
an independent per-operation random HMAC key, sends it over authenticated mTLS
alongside the existing signed policy, and stores it encrypted at rest. The device
persists it on encrypted VFS and omits it from snapshots/support data. MQTT reports
carry only whitelisted lifecycle facts and generic outcomes, never keys, policy
material or raw private errors. Independently verified MACs bind device ID,
operation/release/policy identity, durable revision, boot epoch and sample cursor.
MQTT delivery or QoS alone does not confer trust or exactly-once execution.

Broker host/port, credentials, TLS identity, topic template and recovery intervals
are configurable in Management. Devices reuse their existing trusted TLS broker
connection and reject admission if it differs from the selected host/port.
Default topic: `iotmd/update-operations/{device_id}/{operation_id}`. Identity
placeholders are mandatory; no wildcard topic injection is permitted. The host
receiver is bounded/coalesced and changes no device state. Fresh reports reduce
HTTP polling; periodic/stale/disconnected/cancellation API reconciliation remains.

Management retains bounded per-device work and reserved observation capacity.
Its browser consumes cached projections, never fans requests out directly to
devices. Stop tracking retires only the Management projection and preserves an
unresolved history record; it sends no device commands.

## Remaining implementation and release gates

- Bootstrap Alpha 123 on devices with the portal or the previous Management
  release before upgrading Management to 3.2.12. Test a strictly newer signed
  release once the contract is installed; old uncertain jobs can be Stop tracked.
- Qualify optional MQTT tracking on Alpha 124 / Management 3.2.13. Install both
  updated components before selecting MQTT. API remains the default; Alpha 123 /
  Management 3.2.12 remain API-only. No live broker connection or device changes
  were made while implementing MQTT.
- Resolve generic API admission NVS capacity separately without weakening replay
  suppression; qualify encrypted-VFS durability and reserved update capacity.
- Test native API responsiveness under transfer/signature/flash workload. New
  transport or more host workers do not fix a device event-loop stall.
- Run physical device power-cut/fault-injection and fleet load tests. The user
  approved publication of signed testing releases, but not device installation.
