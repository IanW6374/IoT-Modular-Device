# IoT-MD v3.0.0-alpha.65

Release sequence: 2770. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 65 completes the portal terminology and interaction update. User-facing
Upgrade labels are now Updates, pointer-driven submenus wait briefly before
opening, and the live Device and Audit log status appears beside the title with
its last-refresh time. Changing the Device log level applies immediately; the
stored-line limit remains available in Logging settings.

Release Qualification can reset a blocked Canary Health gate only after the
active fleet pause has been cleared. The failed result remains in the audited
retry history, and the gate returns to not-run so it cannot be treated as passed
without new observations.

Fleet policy format 2 binds each update command to Application, Core or
Universal. Automatic checks filter the signed catalog by both release sequence
and artifact type before compatibility checks and staging.

The native platform ABI is unchanged. Alpha 65 is an application release and
remains compatible with the Alpha 62 native core.
