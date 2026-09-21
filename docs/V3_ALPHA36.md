# IoT-MD v3.0.0-alpha.36

Release sequence: 2741. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

- Qualification retries now shrink older diagnostic history when encrypted NVS
  has less free space than its advertised per-record payload limit. The newest
  archived failure and current summary are retained; unrelated gate counters are
  not reset. If the minimum archive cannot be saved, the gate remains blocked.
- The Automatic upgrade method badge is aligned at the top right of its card,
  alongside the method title, on desktop and narrow screens.

The existing Alpha35 audited retry workflow and explicit staging/activation
remain unchanged. This release does not automatically clear failed gates.

## Device checks

1. Install the universal package and verify core and application Alpha36.
2. Correct the cause of a failed qualification gate, then restart that test with
   a reason and confirmation. Verify the previous failure is retained and other
   gate counters are unchanged. Repeat the required evidence collection: a retry
   must not immediately mark the gate passed.
3. Reboot and confirm the retry history and new test window persist. If encrypted
   storage still cannot hold the minimum record, capture diagnostics rather than
   clearing credential storage or resetting unrelated qualification evidence.
4. Check the Automatic badge placement on desktop and mobile. Continue the
   existing paired-update, power-loss and release qualification campaign.

Host/browser checks are regression evidence, not hardware qualification.
