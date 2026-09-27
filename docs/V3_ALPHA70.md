# IoT-MD v3.0.0-alpha.70

Release sequence: 2775. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 70 is a signed application-only dummy release for testing the managed
upgrade path from Alpha 69. It contains no intentional functional changes
beyond the product and runtime version increment.

Use this release to confirm that IoT-MD Management Suite 2.2.19 sees the
device's active Management signing-key fingerprint, accepts the trust
preflight, signs the policy with the matching identity, and can stage and
activate an immediate deployment.

The application remains compatible with the Alpha 62 native core.
