# IoT-MD v3.0.0-alpha.74

Release sequence: 2779. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 74 is a matched universal application and core release. It fixes manual
universal activation when the device has a fleet policy but is outside that
policy's maintenance window.

An authenticated operator selecting **Restart and install** is now identified
as a manual activation and may proceed immediately. Fleet-managed and automatic
activation continue to require their configured maintenance window.

Because Alpha 73 and earlier route the manual action through the managed check,
this universal bundle carries a signed compatibility bridge that permits its
manual activation. Install the `.iotuni` artifact from the device portal.
