# IoT-MD v3.0.0-alpha.59

Release sequence: 2764. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 59 replaces direct use of CPython's `PermissionError` with a portable
`APIAuthorizationError`. It inherits from `PermissionError` on CPython and
from `Exception` on MicroPython, where the more specific built-in is omitted.

The previous EOF was not a failed TLS upload. Device event history confirmed
that the Home Assistant policy POST was authenticated, read and dispatched.
The empty policy then correctly raised a `ValueError`, but MicroPython raised
`NameError` while evaluating the preceding `except PermissionError` clause.
That secondary error escaped the handler before an HTTP response was written.

This compact application-only update is compatible with the Alpha 52 native
core. Posting an invalid empty policy must return HTTP 400 JSON containing
`unsupported fleet policy format`. A valid signed policy can then expose any
remaining policy-specific validation result instead of an opaque EOF.
