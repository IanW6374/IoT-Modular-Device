# IoT-MD v3.0.0-alpha.67

Release sequence: 2772. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 67 corrects the Device log level selector. The browser now serialises the
selected level before temporarily disabling the control, so the device receives
the requested value rather than rejecting an empty one. The selected option
continues to show the active level, while the adjacent badge is reserved for
live or paused state and its timestamp.

The Device submenu and page now use the concise API label. Enrolled API clients,
scope editing and revocation are shown only under Maintenance, Certificates,
API client trust instead of being duplicated on the listener-settings page.

Release Qualification no longer offers a manual reset for Canary Health. That
gate explains that it clears automatically after the active fleet pause is
resolved; manual restart remains available for failed tests that require fresh
evidence.

The native platform ABI is unchanged. Alpha 67 is an application release and
remains compatible with the Alpha 62 native core.
