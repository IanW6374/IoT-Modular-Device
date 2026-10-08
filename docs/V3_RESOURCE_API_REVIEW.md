# Native resource ownership and Device API v3 review

Reviewed 2026-10-08 against Alpha 107 and Management 2.8.22. This is a source
review and proposed implementation sequence, not a hardware qualification
report. Alpha 108 / Management 3.0.0 now implement the approved v3-only rollout,
production native driver wiring and durable mutation handling described below.
These are local source changes; no installed device was changed during this work.

## Scope decisions

V2 backup migration, compatibility/shadow cutover and USB networking are
retired. Keep encrypted v3 backup/restore, Wi-Fi, USB serial recovery and
diagnostics, signed paired updates and operational qualification. The original
requirement IDs are retained in [the baseline](V3_REQUIREMENTS.md).

Qualification evidence contract 2 has 14 active gates and excludes the retired
`migration-rollback` gate. Prior counters, archived gate outcomes and retry
records remain historical evidence; migration is not manufactured as passed.
Retirement does not waive v3 configuration-restore or paired-update rollback
tests, nor does it qualify the remaining untested gates.

## Native resources: actual implementation boundary

| Layer | Present | Remaining |
| --- | --- | --- |
| Native ABI 7 / core API 15 | Core-owned GPIO/ADC/PWM/UART/SPI/I2C objects, bounded calls, immutable bus configuration, sharing and generation-safe release | Hardware qualification, including reset/IRQ/partial-construction stress |
| Shipped allocator | Preflight claims, protected LED/display resources, owner-bound injection and failed-setup cleanup | Hardware acceptance for actual configured boards |
| Shipped drivers | All 13 catalog types use managed wiring; DHT and pulse reads receive native core helpers | Electrical/timing tests for each installed combination |
| Historical adapter | `v3/runtime/iotmd_next/resources.py` wraps native lifecycle calls | It is not in the production bundle and is not itself a complete driver I/O backend |

Evidence: [native resources](../firmware/native/iotmd_platform_v3.c),
[shipped allocator](../device_modules/resources.py),
[loader](../device_modules/loader.py), [SPI backend](../device_modules/spi_bus.py)
and [bundle allow-list](../tools/build_update.py).

### Resource implementation and acceptance

`device_modules/native_resources.py` and `managed_setup.py` provide the
production path. Native code roots the proven MicroPython peripheral objects
and validates a lease on every call, rather than starting competing ESP-IDF and
`machine` controllers. SPI IDs are explicitly 1/2. Core flash/PSRAM, USB and
console pins are protected. Production setup has no unmanaged fallback.
Direct setup functions remain host driver fixtures, not a product fallback.
Managed recovery requires release/reconstruction rather than live re-init.

The original work/acceptance sequence below is retained; HIL remains due.

1. Define a versioned native I/O contract and bounded configuration, transfer,
   error and timeout limits. Add generation-safe handles so a released handle
   cannot act on a subsequently reused claim slot. Protect core-owned pins,
   memory buses and the recovery console from module claims.
2. Implement a managed GPIO reference driver first, including output safe
   state, input observation, failure cleanup and restart recovery. Do not
   construct an ESP-IDF peripheral and a `machine` peripheral for the same
   resource: they would have independent lifecycle ownership.
3. Add ADC and PWM/timer operations, then UART/RS485/EMS and SPI/I2C transfers.
   Include existing driver needs such as UART framing, receive buffers, SPI
   device configuration, chip-select ownership and PWM frequency/duty.
4. Integrate the existing driver catalog through an injected managed backend.
   Timing-sensitive DHT, pulse measurement and encoder/button helpers need
   explicit native or managed integration; an arbitrary GPIO proxy cannot be
   assumed to work with MicroPython functions expecting a native Pin object.
5. Qualify conflicting claims, compatible shared buses, failed construction,
   stale handles, module stop, soft restart, interrupt pressure and bounded
   transfers on the supported board/driver combinations. Native capability
   flags remain unqualified until those tests are observed.

Bus-number mapping must be explicit: MicroPython SPI identifiers cannot simply
be copied into ESP-IDF host identifiers. Reject incompatible electrical
configuration before touching hardware. Native ownership does not mean exposing
raw ESP-IDF handles or unrestricted peripheral access over the Device API.

## Device API v3: contract before endpoint rename

At review time the deployed router reported `API_VERSION = 2` and served `/api/v2`; Management's
poll, profile, backup, certificate and policy requests hard-code that prefix.
The then-current OpenAPI document was also v2. Product v3 and protocol
v2 are independent version numbers: current API v2 use is not proof of a v2
firmware compatibility path.

Evidence: [router](../device_api.py), [API documentation](API.md), and Management
`iot_md_management/rootfs/app/fleet_service.py` in its separate repository.

### Recommended API v3 contract

- Explicit advertised protocol version, capabilities and per-operation limits.
  Separate immutable hardware identity from mutable hostname and description.
- Bounded device, API/service health, module, resource, release and operation
  projections with documented schemas. Resource state must distinguish a
  compiled mechanism, its integration and observed qualification.
- Uniform structured errors: stable code, safe detail, operation/request ID
  and retryability. Keep mTLS, enrolled-client identity and existing scoped
  permissions; do not make discovery a security bypass.
- A common operation model for long-running mutations: accepted, queued,
  running, waiting for restart, complete and failed, with durable milestone
  results where needed. Immediate label-only edits can remain synchronous.
- Bounded, persistent idempotency handling for mutating requests. The same key
  and payload returns the original operation; a different payload using that
  key fails. A lost response must not cause another update or restore. Retain
  restart-spanning operations without writing flash for every progress sample.
- Specify body, collection, cursor, timeout and storage limits. Complete
  encrypted restore previews remain an explicitly bounded large-body endpoint,
  not a global increase of the HTTP request limit.

### API rollout

The approved rollout is a coordinated breaking update: IoT-MD exposes only
`/api/v3`, and Management verifies that protocol before any operational request.
API v2 is retired, with no aliases or fallback. Existing records, encrypted
backups and historical qualification evidence are retained; this is not a fresh
installation or a deletion of user data. Update devices locally before moving
Management to the matching release. Discovery is read-only and still requires
mutual TLS and the enrolled client's read scope.

The v3 cutover includes discovery, capabilities/limits and structured errors.
Every POST now requires a sequence/nonce idempotency key, committed with a
certificate-scoped watermark to encrypted NVS before side effects. Results live
on encrypted flash, bounded to six records / 768 KiB total. Eviction preserves
watermarks; a lost result or interrupted request never permits re-execution.
Management persists sequences and request keys before sending and serializes
device requests. Operations distinguish request acceptance from module-command
completion; deployment/network-trial telemetry remains authoritative.

See [the operation contract](API.md) for restart semantics and limits. This
provides durable duplicate suppression, not exactly-once physical effects
through power loss. Native capability flags and hardware qualification gates
remain unqualified.

## Proposed delivery order

1. Retire the active migration qualification gate with versioned evidence.
2. Deliver v3-only routes, schemas and strict Management protocol discovery.
3. Deliver the native managed-GPIO reference path in a coordinated core/application
   release, retaining signed paired-update and recovery safeguards.
4. Extend the managed backend to the complete existing driver catalog in small,
   hardware-qualified increments. Native resource progress can be exposed by
   API v3 without blocking the API contract on every physical driver.
5. Extend v3 with durable operation/idempotency contracts and observed hardware
   qualification. Do not reintroduce API v2 compatibility.

Each release needs host and MicroPython checks, signed clean-source artifacts,
interruption/security tests appropriate to its changes and explicit hardware
acceptance evidence. No existing connected device is a fault-injection target
without separate approval.
