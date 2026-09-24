# IoT-MD v3.0.0-alpha.41

Release sequence: 2746. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 41 consolidates the Upgrade tab into one workflow. File and version
selection, verification state, and the manual restart action are aligned with
their progress steps; the duplicate current-task row, divider, and disabled
Working action are removed. Discard aborts an in-progress browser upload and
removes its resumable server state without a page refresh. A verified release
remains staged until the operator explicitly chooses **Restart and install**.
