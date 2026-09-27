# IoT-MD v3.0.0-alpha.69

Release sequence: 2774. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 69 makes the Management Suite fleet-policy trust relationship directly
observable. The CA & signing trust page shows the normalized SHA-256
fingerprint of the active Management Suite key, and a successful replacement
reports the exact fingerprint that was committed.

The read-only fleet state now includes that fingerprint. Management Suite
2.2.19 compares it with its own signing identity before creating a deployment,
so a mismatch reports both values without waiting for ECDSA verification and an
HTTP error response.

The native platform ABI is unchanged. Alpha 69 is an application release and
remains compatible with the Alpha 62 native core.
