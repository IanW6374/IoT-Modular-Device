# IoT-MD v3.0.0-alpha.73

Release sequence: 2778. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 73 is a matched universal application and core release. It updates the
frozen core `update_security` canonicalizer so format-2 fleet-policy command
signatures include `release_type`, matching IoT-MD Management Suite 2.2.20 and
later.

The Alpha 62 core predates typed fleet commands. It validates the same signing
key but hashes a different policy message, so replacing the key cannot resolve
the resulting signature failure. Install the Alpha 73 `.iotuni` artifact from
the device portal using Manual or Automatic update; a fleet-managed deployment
cannot cross this compatibility boundary.

The native platform ABI remains 6. This release changes frozen Python core
policy code rather than the native C ABI.
