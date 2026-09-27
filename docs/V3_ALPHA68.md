# IoT-MD v3.0.0-alpha.68

Release sequence: 2773. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 68 streamlines the Update page by removing the duplicate release-status
banner and retaining availability in the Automatic method badge. Automatic
updates now expose Discard before and throughout download and staging. An
in-flight discard interrupts the transfer, clears partial staged state and
leaves the workflow ready for another attempt, matching manual updates.

Device log now opens at the newest entries so the current activity is visible
without an initial scroll. Earlier entries remain available by scrolling up.

Device qualification is divided into four focused submenu pages: Summary,
Tests, Evidence and Platform. Existing actions and evidence are retained, but
the common gate overview is no longer mixed with disruptive controls and
implementation detail on one long page.

The native platform ABI is unchanged. Alpha 68 is an application release and
remains compatible with the Alpha 62 native core.
