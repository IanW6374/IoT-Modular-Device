# IoT-MD v3.0.0-alpha.34

Alpha34 uses release sequence 2739 and retains native platform ABI 6.

Maintenance > Upgrades > Upgrade now opens the common workflow directly.
Automatic and Manual methods are always visible; Staged appears only when a
verified release exists, and Rollback only when a previous application is
retained. Rollback remains application-only and is labelled accordingly.

Choose an automatic version or a signed local file, then select **Stage upgrade**.
The circular milestones follow the selected artifact type and remain consistent
when staging completes. Staging does not reboot the device: the verified release
can be left staged for later, restarted explicitly, or discarded before selecting
another release. Release checks run inline; status and history are collapsible.

The horizontal track no longer depends on inline style attributes blocked by the
portal's Content Security Policy. On narrow screens it becomes a vertical track.

At the user's request, this release updates the exact ESP-IDF pin from 5.5.1 to
5.5.5 (`b774170ff46c393eeb5e495ea37936038d3f4f4f`) in both the build lock and CI.
MicroPython remains 1.29.0 at its existing pinned commit. Host/browser/build checks
do not qualify this SDK pairing on hardware; follow the
[Alpha34 device test](qualification/v3.0.0-alpha.34.md) before promotion.
