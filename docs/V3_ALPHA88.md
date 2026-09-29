# IoT-MD v3.0.0-alpha.88

Release sequence: 2793. Native ABI: 6. Required runtime core API: 12.

Alpha 88 completes interrupted-universal recovery. Before resuming an existing
transport plan, the device compares both live release sequences with the signed
pair. A component already installed at the same sequence is satisfied and
skipped; only the missing component is uploaded. A component newer than the
offered pair still rejects the release as a downgrade.

The Updates page also retains Alpha 87's persistent Incomplete update and
Discard state, and never offers an inner universal component for independent
activation.
