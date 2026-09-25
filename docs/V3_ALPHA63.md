# IoT-MD v3.0.0-alpha.63

Release sequence: 2768. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 63 extends the concise, graphical Upgrade interaction model across the
authenticated portal. Routine configuration and administration actions now
return structured results, update the affected workspace in place and preserve
the page context instead of navigating through a complete page response.

Settings use consistent sticky save and discard controls, secondary actions use
an outline treatment, destructive actions remain red, and unsaved-change
warnings only apply to forms that can actually lose edits. Certificate
operations, API client management, user management, staged-upgrade discard and
configuration restore refresh their affected sections without a full page
redirect.

Release qualification now explains the controlled campaign as five ordered
steps: review gates, select a scenario, execute and recover, verify the
observation, and record evidence. Restart/reconnect pages remain reserved for
operations that really interrupt the session.

The native platform ABI is unchanged. Alpha 63 is published as an application
artifact and remains compatible with the Alpha 62 native core.
