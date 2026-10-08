# Device API v3

The Device API is a JSON HTTPS interface for inventory, state, diagnostics,
commands, events, support data and fleet coordination. It listens on port 8444
by default and always requires mutual TLS. The machine-readable contract is
[`openapi.yaml`](openapi.yaml).

Alpha 108 replaces API v2 outright. Only `/api/v3` is supported; authenticated
v2 requests return HTTP 410 with `unsupported_api_version`. There are no aliases
or fallback. Upgrade devices locally, then install Management 3.0.0. Existing
configuration and Management records are retained; no fresh install is needed.

The router consumes transport-neutral `APIRequest` objects and returns
`APIResponse` objects. HTTPS/mTLS is the supported external adapter. USB serial
recovery remains independent; USB networking is no longer a requirement.

`GET /api/v3` requires the enrolled client's `read` scope and advertises the
protocol, enabled services and actual body/connection limits. Every HTTP JSON
response includes `api_version: 3`. Errors contain `error.code`, `error.message`
and `error.retryable`. Do not infer mutation success from a timeout or retry an
ambiguous write. Durable reservations suppress duplicate mutations, while
interrupted outcomes require reconciliation; see the operation contract below.

Its server certificate is stored independently from the web portal identity
and is expected to chain to the private IoT CA. A public portal renewal never
changes the Device API/fleet server identity.

## TLS identities and trust

Mutual TLS performs two independent checks:

- IoT-MD authenticates the client certificate against an installed API-client
  CA, then applies the fingerprint registration and scopes described below.
- The API client authenticates IoT-MD against its private IoT CA. The API
  server certificate must contain the exact device hostname, such as
  `iot-md-001.local`, in a DNS Subject Alternative Name (SAN).

The client certificate and key supplied to `curl` prove the caller's identity;
they do not make the workstation trust the server. Supply the private IoT CA
root, plus any required intermediate, with `--cacert`. IoT-MD installs its API
server identity as a leaf-plus-intermediate chain, but using a complete CA
bundle on the client also supports diagnostic and older installations. Do not
use `-k` to bypass verification.

## Authentication and authorization

Install one or more API client CAs under **Maintenance > Certificates > API
client trust**, then
enable the listener under **Device > API**. Each client certificate is
registered by SHA-256 fingerprint with a label and scopes. Read requests require
`read`, module commands require `write`, fleet reads require `fleet:read`, fleet
changes require `fleet:write`, controlled evidence requires `qualification:write`,
configuration-profile changes require `configuration:write`, and disruptive
scenarios require `qualification:execute`. Revocation is checked for every request,
including requests on reused TLS connections.

## Durable mutations and operations

Every POST requires `Idempotency-Key: sequence.hex_nonce`. Obtain the next
sequence from authenticated `GET /api/v3`; choose a fresh 16–32 digit lowercase
hex nonce. Send mutations sequentially for each device/client certificate.
Management allocates sequences and records request keys durably before sending.
Discovery advertises storage limits and `persistent_idempotency`; if encrypted
storage is unavailable, reads work but writes fail closed with 503.

The encrypted-NVS reservation and watermark are committed before any side
effect. The same certificate/key/method/path/body replays its retained result;
changed content returns 409. Even after result eviction, a consumed sequence
cannot execute again. Use the exact original request bytes when reconciling.
Duplicate `Idempotency-Key` HTTP headers are rejected.

Successful writes include an `operation` with ID, request key, state and
`completion_scope`. `request` completion means the callback returned (for example
settings were saved or restart was scheduled), **not** that a deployment or
network trial succeeded. Fleet/update telemetry remains authoritative for those
workflows. `module_command` completion follows the broker's device result.

`GET /api/v3/operations`, `/operations/{id}` and `/operations/{id}/result` expose
only this certificate's retained operations and require read scope. At most six
operations and 16 client watermarks are retained; results are bounded to 384 KiB
each and 768 KiB total on encrypted flash. Terminal results may be evicted to
maintain those bounds, but client watermarks are never automatically discarded.
Progress samples do not trigger flash writes. Clean recovery erases user state
and starts a new provisioning identity boundary; it is not a retry mechanism.

A queued/running operation at restart becomes `interrupted`: its effect may or
may not have happened, so reconcile current state. The device never reconstructs
or repeats its command from the journal, and Management never auto-retries an
ambiguous write. The journal does not store request bodies, passwords or keys.
This guarantees duplicate suppression, not exactly-once physical effects across
a power failure. Private results retain mTLS, scope and revocation checks.

An administrator can expand or reduce an existing caller's permissions under
**Maintenance > Certificates > API client trust**.
Open **Edit API scopes**, select one or more permissions, and save. The registry
updates the existing fingerprint in place, so the certificate does not need to
be uploaded again. At least one supported scope must remain.

The API accepts up to 32 requests on one HTTP/1.1 keep-alive connection and
holds an idle connection for at most 30 seconds. Reuse the connection: a TLS
handshake is substantially more expensive than a JSON request on ESP32-S3.

## Endpoints

| Method | Path | Scope | Result |
| --- | --- | --- | --- |
| GET | `/api/v3` | `read` | Protocol, capability and limit discovery |
| GET | `/api/v3/device` | `read` | Identity, versions, uptime, release sequences and bounded release-qualification state |
| GET | `/api/v3/interfaces` | `read` | Wi-Fi, MQTT, API, syslog and USB NCM state |
| GET | `/api/v3/hardware` | `read` | Board, runtime capability, USB/NCM gates, drivers and resource bindings |
| GET | `/api/v3/services` | `read` | Lifecycle, boot and effective feature-flag state |
| GET | `/api/v3/configuration` | `read` | Bounded non-secret operating configuration |
| POST | `/api/v3/configuration/profile` | `configuration:write` | Validate and apply selected settings and protected secrets; reports restart/trial requirements |
| POST | `/api/v3/configuration/backups` | `configuration:write` | Create an encrypted complete backup |
| POST | `/api/v3/configuration/backups/preview` | `configuration:write` | Validate and preview a bounded encrypted restore |
| POST | `/api/v3/configuration/backups/apply` | `configuration:write` | Apply the previously previewed restore token |
| POST | `/api/v3/configuration/certificates/{kind}` | `configuration:write` | Stage an allowlisted certificate/key file |
| POST | `/api/v3/configuration/certificates/apply` | `configuration:write` | Validate and apply staged certificates |
| POST | `/api/v3/configuration/network/confirm` | `configuration:write` | Confirm a ready network rollback trial |
| POST | `/api/v3/configuration/restart` | `configuration:write` | Request configuration restart |
| GET | `/api/v3/device/inventory` | `read` | Combined device, module and fleet inventory |
| GET | `/api/v3/health` | `read` | Bounded health counters and observations |
| GET | `/api/v3/events?cursor=0&limit=32` | `read` | Cursor-based event page |
| GET | `/api/v3/support` | `read` | Redacted support snapshot |
| GET | `/api/v3/modules` | `read` | Module catalog and capabilities |
| GET | `/api/v3/modules/{uuid}/state` | `read` | Current transport-neutral state |
| GET | `/api/v3/modules/{uuid}/diagnostics` | `read` | Driver diagnostics |
| POST | `/api/v3/modules/{uuid}/commands` | `write` | Queued operation (`202`) |
| GET | `/api/v3/operations/{id}` | `read` | Operation status |
| GET | `/api/v3/operations` | `read` | This client's bounded retained operations |
| GET | `/api/v3/operations/{id}/result` | `read` | This client's last durable operation result |
| GET | `/api/v3/fleet` | `fleet:read` | Fleet enrollment and policy state |
| POST | `/api/v3/fleet/policy` | `fleet:write` | Apply a monotonic signed policy |
| POST | `/api/v3/fleet/commands/{id}/result` | `fleet:write` | Complete a fleet command |
| GET | `/api/v3/qualification` | `read` | Full on-device qualification status and evidence |
| POST | `/api/v3/qualification/events` | `qualification:write` | Append one observed controlled-test outcome |
| POST | `/api/v3/qualification/scenarios/{name}` | `qualification:execute` | Start an allowlisted disruptive Alpha-only test |

Configuration profiles may contain standard operational settings such as time,
logging, Home Assistant discovery, MQTT routing, Wi-Fi and remote syslog.
Allowlisted Wi-Fi/MQTT passwords use the separate protected `secrets` object;
certificate/key files use the staged certificate endpoints. Configuration reads
never expose these values. The profile is validated before storage, application
is audited, and the result reports whether a restart or network rollback trial
is required. Description-only edits do not require a restart.

Qualification event submissions require a controlled gate, `success` or
`failure`, a bounded run ID and explicit confirmation. They append an observation;
they cannot set a gate status directly. Available disruptive scenarios are
`watchdog-recovery` and `native-recovery`. Scenario execution never records a
success automatically: an independent observer must verify recovery and submit
the resulting evidence.

UUIDs are the configured four-digit hexadecimal module IDs. State keys and
command bodies are driver-specific and are documented in the
[module guide](modules/README.md). A command returns an operation record
immediately; poll its URL until `status` is `complete` or `failed`. A restart
before a durable outcome is recorded reports `interrupted`; reconcile device
state rather than submitting the command again.

## Example

```sh
cat home-iot-intermediate.pem home-iot-root.pem > home-iot-ca-bundle.pem

curl --fail-with-body \
  --cacert home-iot-ca-bundle.pem \
  --cert api-client.pem \
  --key api-client-key.pem \
  https://iot-md-001.local:8444/api/v3/modules/00A1/state
```

```json
{"module":"00A1","state":{"temperature":21.7,"humidity":48}}
```

Routine GETs increment aggregate counters but are logged only at debug level;
mutating calls create health and audit records. Responses are `no-store` JSON.
Typical failures are `400` malformed input, `401` missing/invalid identity,
`403` insufficient scope, `404` unknown endpoint/module/operation, `409`
idempotency conflict or uncertain outcome, `413`
oversized input and `503` temporarily unavailable service.

New clients should request only the smaller projection they need. The combined
inventory endpoint is retained for existing management-suite clients but should
not be used as a frequent polling endpoint. Configuration output contains no
Wi-Fi/MQTT passwords, private keys, certificate payloads or password verifiers.
USB diagnostics distinguish `usb_device`, `usb_ncm_hardware`,
`usb_ncm_runtime` and `usb_ncm_available`; clients must use the last value for
effective availability rather than inferring support from the runtime symbol.
Alpha 7 additionally shows the native ABI 4 update, recovery and bounded-job
mechanisms in the on-device Release Qualification view. Mechanism availability
and HIL qualification are separate values; clients must not treat an exported
entry point as proof that rollback or recovery qualification passed.
Alpha 9 advances this report to ABI 5 and adds physical resource mechanism and
qualification fields. Resource inventory exposes only bounded claim metadata,
sharing configuration and constructed state; ESP-IDF pointers and physical
credential locators never enter the API.
Alpha 10 advances the report to ABI 6 and adds a bounded native paired-journal
snapshot plus nine implementation-gate records. `implemented` reports code
presence; `qualified` reports observed production evidence. Clients must not
infer the latter from the former.
Alpha 16 retains that report contract. During a trial, the application version
reports the slot actually executing; the active slot remains uncommitted until
native core confirmation and application commit both succeed. A terminal
universal state must use exact matching core and application release sequences.
Alpha 6 reports each release-qualification gate as a bounded name/status pair;
full measurements remain in the on-device Maintenance view and qualification
evidence file rather than expanding routine API polling payloads.
