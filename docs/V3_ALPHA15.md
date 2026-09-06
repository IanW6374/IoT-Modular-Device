# IoT-MD v3.0.0-alpha.15 test note

## Purpose

Alpha 15 incorporates the manual-upgrade and Grove AC Voltage calibration
feedback collected after Alpha 14. It does not change the native ABI, signed
upgrade transaction, activation order or rollback behavior.

## Included

- Manual staging shows one file-specific workflow and one current-task progress
  area. Once staging begins the selected filename is hidden; Cancel returns to
  file selection, and both actions remain at the lower right.
- Grove AC Voltage calibration is written atomically, read back before success
  is reported, and retains the previous module-settings generation for
  recovery.
- The active calibration multiplier and offset are visible in Module
  Diagnostics after calibration, restart and upgrade.
- Linked overview tiles retain one whole-tile hover treatment and a visible
  keyboard focus ring; label and value text do not acquire a second highlight.

## Expected behavior

Install `universal-3.0.0-alpha.15.iotuni`. Both Application version and Core
version must show `3.0.0-alpha.15` after activation and remain there after a
normal restart and power cycle. Calibrate a Grove AC Voltage module before the
upgrade, record its displayed multiplier, and verify the same value remains
after activation and restart.

## Safety and rollback

The release sequence is `2720` and the native platform ABI remains 6. Alpha 15
retains Alpha 13's legacy paired-state migration and Alpha 12's native-first
confirmation, precise failure recording and power-loss recovery protections.
