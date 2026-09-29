# IoT-MD v3.0.0-alpha.86

Release sequence: 2791. Native ABI: 6. Required runtime core API: 12.

Alpha 86 is the Core API 11 to 12 bootstrap release. Its universal package is
firmware-first and contains a private, signed application component with a
Core API 11 staging floor. The application is activated only as part of the
paired transaction after the bundled Core API 12 firmware has been selected.

The separately published application component retains the truthful Core API
12 requirement and is not installable on Core API 11.

Use the universal package when updating an Alpha 83/84 device with Core API
11. Do not extract or separately install the universal package's private inner
application component.
