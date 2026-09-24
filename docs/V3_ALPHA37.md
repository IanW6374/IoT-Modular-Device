# IoT-MD v3.0.0-alpha.37

Release sequence: 2742. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 37 makes the controlled cross-release campaign operable without an
interactive device console. Administrators can append observed results from
Maintenance > Release qualification. HIL automation can use separately scoped
mTLS endpoints to read the complete ledger, submit controlled evidence and
initiate an allowlisted watchdog or native-recovery scenario.

Evidence submission does not accept a desired gate status. It records one
success or failure and leaves the existing qualification policy to derive the
result. Failures remain sticky and use the Alpha 35 audited retry workflow.
Simulation output is deliberately non-qualifying.

## Device checks

1. Install the Alpha 37 universal release and verify application/core versions
   and release sequence 2742.
2. Enrol a qualification automation certificate. Confirm an ordinary `write`
   client cannot submit evidence or start scenarios.
3. Submit one controlled success and failure through both portal and API;
   confirm counters, audit events and sticky-failure behaviour.
4. Run the automated watchdog HIL command three times. Confirm each run observes
   a higher boot count and watchdog reset cause before recording success.
5. Initiate native recovery and verify the signed frozen recovery environment
   starts before product code. Restore the confirmed pair, then record the
   observed result separately.
6. Run `tools/simulate_qualification.py`; verify its report says
   `evidence_class: simulated-regression` and `qualifying: false`.

Alpha 37 retains the ABI 6 campaign evidence across the release transition.
