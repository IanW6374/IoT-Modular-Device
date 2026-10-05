# Pinned MicroPython transport patch

`tls-listener-cleanup.patch` applies to MicroPython v1.29.0 commit
`0fd6c573ea815774668bbb16b8e197c8822368b2`. The core build validates the clean
upstream checkout, applies the project-owned patch, and reverses only that
patch in `finally`, including after a failed build.

Fatal asynchronous TLS handshakes close the underlying TCP socket immediately,
including certificate-verification failures, preserving the original error.
The accept loop closes accepted sockets on TLS-wrap/allocation failures and
closes its listening socket on any terminal failure. It exposes `is_serving`
and a transport-error callback to the frozen `tls_listener` supervisor.

The supervisor detects failed accept loops every five seconds and rebinds with
bounded retry backoff up to sixty seconds. Intentional closure/certificate
reload cancels supervision. It does not reboot the device, weaken TLS trust,
or replay application operations.

Diagnostics contain only service/stage, peer IP, exception class/errno, Python
heap availability and native internal/DMA free/largest-block sizes. Native
allocation details therefore reach the normal device/syslog logging path
without exposing credentials, request payloads or certificates.
