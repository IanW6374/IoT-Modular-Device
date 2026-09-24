# IoT-MD v3.0.0-alpha.56

Release sequence: 2761. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 56 changes the Device API request-body reader used by fleet policy,
qualification and module-command POST endpoints. Small bodies are now read
using the exact remaining Content-Length. Previously the buffered reader could
inflate a two-byte body read to 512 bytes; when TLS delivered headers and body
in separate records on MicroPython, the device closed the connection before
dispatch and returned no HTTP response or application log.

Device testing showed that this was incomplete: the same read-ahead remained
in header parsing and the EOF symptom persisted. Alpha 57 removes that adapter
from the Device API request path.

This is an application-only update compatible with the Alpha 52 native core.
This release is superseded by Alpha 57 for Device API POST testing.
