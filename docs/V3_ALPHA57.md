# IoT-MD v3.0.0-alpha.57

Release sequence: 2762. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 57 removes the portal read-ahead adapter from the mTLS Device API. The
API continues to enforce bounded request lines, headers and bodies, but reads
them directly from the TLS stream. This restores the byte-sized header parser
that was used before the regression: on the device's MicroPython TLS stream a
large read may wait for the entire requested size even when a complete HTTP
header record is already available.

The symptom was a successful TLS handshake and complete client upload followed
by an unexpected EOF, with no API request event in the device log. Alpha 56
made body reads exact but left the initial 512-byte header read-ahead in place.

This is an application-only update compatible with the Alpha 52 native core.
Device testing showed that POST still ended with an EOF because peer
certificate inspection occurred between the header and body reads. Alpha 58
supersedes this release for Device API POST testing.
