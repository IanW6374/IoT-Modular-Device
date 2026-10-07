# Core transport diagnostics

These diagnostics investigate devices that still respond to ping/TCP but stop
serving the API or portal. They are native/frozen-core facilities, not an
application fallback. Installing them requires a core update. Host tests and
a successful firmware build do not establish the original failure's cause.

## Capture

Keep the existing receive-only USB UART capture open. Do not reopen its serial
port or send console interrupts to obtain normal snapshots: either can disturb
the fault. A console interrupt stops application execution and an enabled
watchdog can then reboot the board.

The native `IoT-MD-Transport` logger emits one line per 60 seconds while a
tracked listener is open. It reports every 30 seconds when the frozen monitor's
heartbeat is at least 15 seconds old, a native TLS call lasts at least 10
seconds, a pending handshake lasts at least 30 seconds, or the largest free
internal block is below 4 KB. Intentional shutdown of all tracked listeners
does not produce stale-heartbeat warnings.

The ESP timer uses no Python callback, GC operation or network I/O. Records are
fixed-size and contain no requests, credentials, certificates, hostnames or
client identities. Output is native UART logging, not remote syslog, so it can
be captured when Python logging or the network is stalled.

## Interpretation

| Field | Meaning |
| --- | --- |
| `vm_age_ms` | Time since a frozen listener monitor last ran; not proof that every application task is healthy. |
| `sockets`, `listeners` | Open sockets owned by MicroPython's socket module and the listening subset. Native IDF/DNS sockets are outside this inventory. |
| `accepts`, `accept_age_ms` | Successful TCP accepts and age of the most recent accept; an idle server naturally has a large age. |
| `tls`, `pending`, `wait_ms` | Tracked TLS sockets, incomplete handshakes and oldest incomplete-handshake age. |
| `call_stage`, `call_ms` | Longest currently executing native TLS call: 0 idle, 1 setup, 2 explicit handshake, 3 read, 4 write. |
| `progress_age_ms` | Age of the latest completed handshake or positive native TLS read/write result. |
| `tls_errors`, `last_error` | Native TLS errors, excluding ordinary WANT_READ/WANT_WRITE and clean closure. |
| `internal_free`, `internal_largest`, `internal_min` | Current internal free bytes, largest free block and low-water free bytes. These differ from Python/PSRAM free memory. |
| `overflow` | Events that exceeded the bounded tracking capacity; inventory is incomplete if nonzero. |

`_iotmd_platform.transport_resources()` exposes these counters alongside DMA
and internal memory figures for existing transport-failure reports. Socket
open/close and TLS open/close totals are also included in that snapshot.

A high heartbeat age supports an event-loop progress problem; a young heartbeat
with old pending TLS connections points to a narrower transport problem.
Neither memory fragmentation nor a TCP accept alone proves a TLS fault's
cause. Correlate snapshots, API/portal behaviour and the surrounding UART log.

Diagnostics do not restart devices, close sockets, bypass TLS verification,
change socket limits or alter update/confirmation/watchdog policy.
