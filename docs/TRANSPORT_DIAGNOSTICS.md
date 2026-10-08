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

Alpha 104 enables INFO/WARN output specifically for the `IoT-MD-Transport`
native logging tag before the timer starts. The product-wide ERROR threshold
remains unchanged. Alpha 103's counters work, but its periodic UART snapshots
are suppressed by that default threshold; install the Alpha 104 core to receive
them. No device console commands or application logging workaround are needed.

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

## Internal-memory allocation tracing (opt-in diagnostic core)

The Alpha 104 capture on 7 October showed a roughly 21–23 KB/hour decrease
in internal free memory across three devices. Two eventually timed out during
TLS handshakes. One logged hardware AES allocation errors with a largest DMA
block of just 704 bytes, despite approximately 7 MB of free Python heap. This
establishes allocation pressure, not the identity of the long-term allocation
owner. A separate SDK AES partial-allocation cleanup defect is regression-tested
and patched in the core build; it must not be presented as a proven explanation
for the earlier steady decline.

A subsequent source audit found an independent, definite ownership leak:
the pinned MicroPython `esp32.NVS` constructor opens an IDF namespace handle,
but has no close method or finaliser. IDF retains two native handle objects
until `nvs_close` is called. The frozen credential store opens a namespace on
routine reads, including missing network-trial/configuration keys, so those
reads accumulate internal allocations that Python GC cannot release.

The core patch adds an idempotent `close`, a finaliser and context-manager
support to `esp32.NVS`. It allocates the Python wrapper before opening the
native handle, avoiding a further leak if wrapper allocation fails. All frozen
credential-store transactions use context-managed closure on success, early
return and exceptions; no periodic GC or application-level caching workaround
is used. Closing does not commit implicitly, so existing atomic credential
write/commit ordering is preserved. Native lifecycle and frozen-store
regressions exercise repeated operations without GC. An on-device soak is
still required to confirm that this removes the observed long-term decline
and to identify any remaining allocation owners.

Use `--heap-trace` with `tools/build_micropython_firmware.py` to build a
diagnostic core. Normal builds explicitly pass `IOTMD_HEAP_TRACE=OFF` and
regenerate sdkconfig, so a previous diagnostic build cannot silently enable
tracing in a later production build. Security configuration remains unchanged.
The pinned IDF patch is applied only during the build and restored even if a
MicroPython patch or compilation fails.

The existing frozen-core heartbeat advances native tracing; no additional
Python task, network endpoint, console command or ESP-timer allocation callback
is added. After a 90-second warm-up, each window records allocations for
120 seconds, pauses new allocation records, allows 45 seconds for late frees,
then stops tracing before reporting. Three windows run, with ten minutes
between windows; afterwards the record buffer is detached and released.
The first report normally arrives about 4 minutes 15 seconds after the first
heartbeat. A stalled VM delays this tracing workflow; independent transport
timer snapshots continue unchanged.

Storage is bounded to 2048 trace records in PSRAM and 32 grouped call stacks.
IDF's trace hash map is also placed in external RAM. Six-frame native call
stacks identify allocation callers; no heap contents, request bodies, client
identities, credentials, certificates or keys are read or logged. UART reports
include retained internal allocation counts/bytes, start/end free memory,
record high-water mark, overflow and omitted-group totals. Allocations made
from ISRs are excluded by the SDK when trace storage is in external RAM.

`IoT-MD-Heap` reports **retained allocations**, not automatically proven leaks:
some legitimately long-lived allocations and unreachable Python objects whose
native finalisers have not run may remain. Correlate repeated windows with
normal request traffic and internal-memory trends. Overflow or omitted groups
make the report incomplete and are reported explicitly. Tracing adds native
allocator overhead while enabled and should first be installed on one test
device; do not install it fleet-wide to investigate a single failure.

Keep the exact diagnostic `micropython.elf`, sdkconfig and signed core together.
Resolve the `pcs=` addresses using the pinned Xtensa toolchain's
`xtensa-esp32s3-elf-addr2line -a -f -C -i -e micropython.elf`.
An ELF from another build can map addresses to unrelated code. Installing a
diagnostic core requires a normal verified core update/restart; a receive-only
capture cannot enable tracing on an already installed Alpha 104 image.
