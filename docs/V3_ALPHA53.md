# IoT-MD v3.0.0-alpha.53

Release sequence: 2758. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 53 adds administrator-managed API scope editing for certificates that are
already enrolled. The Device API and API Client Trust pages expose the same
multi-select editor. Saving replaces only the selected scopes on the existing
fingerprint; it does not create a second trust record or alter the certificate's
identity metadata.

The editor supports `read`, `write`, `fleet:read`, `fleet:write`,
`qualification:write` and `qualification:execute`. It rejects empty or unknown
scope sets, applies valid changes immediately and records the change in runtime
health history. This allows an existing automation identity to be authorised
for controlled qualification evidence and watchdog execution without issuing a
duplicate certificate.

Alpha 53 is an application-only signed release. It remains compatible with the
Alpha 52 native core (ABI 6). Promotion still requires physical evidence under
the [Alpha 53 qualification plan](qualification/v3.0.0-alpha.53.md).
