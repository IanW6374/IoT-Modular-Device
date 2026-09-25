# IoT-MD v3.0.0-alpha.64

Release sequence: 2769. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 64 fixes the Alpha 63 nested-navigation and managed-upgrade regressions.
Maintenance submenus now use delegated click handling with pointer and keyboard
fallbacks, and the disruptive qualification action remains aligned at the
bottom-right of its panel.

Exact-sequence release checks no longer call a helper that may be absent from
the already-loaded Alpha 62 native-core copy of `release_update`. Automatic
checks and Management Suite policies therefore work without requiring a core
upgrade.

The native platform ABI is unchanged. Alpha 64 is an application release and
remains compatible with the Alpha 62 native core.
