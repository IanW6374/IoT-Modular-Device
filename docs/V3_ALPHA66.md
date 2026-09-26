# IoT-MD v3.0.0-alpha.66

Release sequence: 2771. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 66 refines the portal interaction changes introduced in the preceding
alpha releases. Update checks now remain on the current page, Automatic and
Manual selections use the same visual order, and the Start update action sits
beside Discard. The final progress milestone has one correctly rendered primary
Restart and install control with its connector masked behind it.

The redundant top-level Status menu has been removed. The Device log badge now
includes the active log level alongside its live or paused state and refresh
time, successful log-level notices are suppressed, and the log filter example
is simplified. Device API save and discard actions are presented directly in
the listener panel without an additional inset section.

The native platform ABI is unchanged. Alpha 66 is an application release and
remains compatible with the Alpha 62 native core.
