# IoT-MD v3.0.0-alpha.18

Alpha 18 is a corrective power-cycle and qualification-evidence release. It
adds no new greenfield architecture mechanism and retains native platform ABI
6.

## Changes

- Accept warning-level legacy events and safely normalise unknown severities so
  logging cannot cause a startup failure.
- Isolate retry diagnostic callbacks from Wi-Fi control flow. A transient
  association failure therefore continues through the bounded three-attempt
  policy instead of falsely requesting recovery.
- Preserve the existing rollback-compatible current-release qualification
  record and add a separate encrypted ledger containing compact summaries for
  the four preceding releases.
- Identify automatic device observations and controlled qualification tests in
  the portal, while exposing the controlled-event methods through the runtime
  bridge.
- Improve the spacing between the manual-upgrade filename and its pre-selection
  guidance.

## Architecture status

All planned greenfield implementation mechanisms remain present. Promotion is
still blocked on release-bound hardware qualification, shadow parity and
controlled cutover evidence. The compatibility path remains intentionally
available as rollback and recovery protection until those gates pass.
