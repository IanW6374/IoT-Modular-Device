# IoT-MD v3.0.0-alpha.38

Release sequence: 2743. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 38 corrects the Alpha 37 startup regression by constructing the
qualification-control service only after the runtime logging function exists.
This prevents the `logOutput` name error that caused the application trial to
fail and automatically roll back.

The Upgrade method choices now retain a consistent width as Staged and Rollback
choices appear, do not underline their contents on hover or keyboard focus, and
collapse to a single full-width column on small displays. Every staged artifact
uses the concise **Restart and install** action, whether it contains an
application, core firmware or a universal pair.

Alpha 38 retains the Alpha 37 controlled qualification API, portal workflow and
HIL tooling. It also retains native ABI 6 and the current cross-release evidence
campaign.
