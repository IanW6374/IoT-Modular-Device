# IoT-MD v3.0.0-alpha.60

Release sequence: 2765. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 60 normalizes the runtime clock to Unix time before comparing it with a
signed fleet policy's `not_before` and `expires_at` values. ESP32 MicroPython
uses 1 January 2000 as timestamp zero, whereas the Management Suite and signed
policy contract use the Unix epoch. The previous comparison therefore placed a
new policy roughly 30 years in the future.

The same normalization is applied to recorded fleet result timestamps. Local
maintenance-window evaluation continues to use the device's configured
timezone and the native runtime clock.

Managed deployment commands now check the channel carried by the signed policy
and select its exact release sequence rather than inheriting the device's
interactive portal channel. A stage-and-install deployment leaves activation
pending, without recording a failure, until its local maintenance window
opens.

This is a compact application-only update compatible with the Alpha 52 native
core.
