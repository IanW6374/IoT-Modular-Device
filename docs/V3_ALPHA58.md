# IoT-MD v3.0.0-alpha.58

Release sequence: 2763. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 58 receives the complete bounded Device API request, including its body,
before extracting the authenticated peer certificate from the MicroPython TLS
stream. The listener's SSL context still requires and verifies the client
certificate during the handshake; only application-level identity extraction
is deferred.

On the device TLS implementation, calling `getpeercert()` between header and
body reads can prevent the stream from yielding the remaining application
data. The result was a successful mutual-TLS handshake and upload followed by
an unexpected EOF, with no request dispatch.

This is a compact application-only update compatible with the Alpha 52 native
core. Device testing proved that requests reached dispatch, but error handling
still closed the connection because MicroPython omits the CPython
`PermissionError` class used by the first exception clause. Alpha 59
supersedes this release for Device API POST testing.
