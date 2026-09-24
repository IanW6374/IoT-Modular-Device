# IoT-MD v3.0.0-alpha.61

Release sequence: 2766. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 61 adds a bounded configuration-profile endpoint for IoT-MD Management
Suite. A caller must have the dedicated `configuration:write` scope. Profiles
can standardize time, logging, Home Assistant discovery, MQTT routing and
remote-syslog settings. The device validates the complete profile, writes the
settings atomically, records an audit event and reports that a restart is
required.

Passwords, certificates, API trust, device identity and network addressing are
not accepted by this profile format. Mutual TLS protects profile delivery in
transit; a later secret-profile format can add encrypted-at-rest storage in the
Management Suite without weakening this non-secret contract.

This is a compact application-only update compatible with the Alpha 52 native
core.
