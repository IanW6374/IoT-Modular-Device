# IoT-MD v3 requirements baseline

V3 preserves the user-visible capability of stable v2.5 while changing its
implementation boundaries. Each requirement has one primary owner.

Scope reviewed on 2026-10-08 against Alpha 107. The table below is the active
baseline, not a claim that each requirement has passed hardware qualification.
See [native resources and Device API v3 review](V3_RESOURCE_API_REVIEW.md) for
the remaining integration work and proposed delivery sequence.

| ID | Requirement | Owner |
| --- | --- | --- |
| PLAT-01 | Recover and accept a signed release without a product runtime | Platform |
| PLAT-02 | Enforce secure boot, flash encryption and encrypted secret storage | Platform |
| PLAT-03 | Provide paired platform/runtime trial, confirmation and rollback | Platform |
| PLAT-04 | Expose bounded boot, reset, heap, storage and capability diagnostics | Platform |
| PLAT-05 | Own physical resources, including driver-required PWM/timers, and provide qualified Wi-Fi interfaces | Platform |
| RUN-01 | Validate, version and transactionally migrate configuration | Runtime |
| RUN-02 | Supervise services and modules with bounded health/event history | Runtime |
| RUN-03 | Support declarative resource-aware modular drivers | Runtime |
| RUN-04 | Provide MQTT and optional Home Assistant discovery | Runtime |
| RUN-05 | Provide role-aware HTTPS portal and mTLS Device API v3 | Runtime |
| RUN-06 | Orchestrate certificate enrollment, renewal and trust administration | Runtime |
| RUN-07 | Provide audit, syslog, support and connectivity diagnostics | Runtime |
| REL-01 | Publish one ordinary universal artifact with SBOM and provenance | Host/platform |
| REL-02 | Enforce monotonic release sequence and component compatibility | Platform |
| FLEET-01 | Report bounded inventory, health and release state | Runtime |
| FLEET-02 | Apply signed scoped policy and support canary rollout | External/runtime |
| QUAL-01 | Pass host, HIL, interruption, rollback and soak gates | Host/HIL |
| QUAL-02 | Bind persistent evidence to one release and report readiness only when every active qualification gate passes | Runtime/platform |

## Retired requirements

The following were retired by the product owner on 2026-10-08:

- **REL-03: v2 backup migration.** No v2-to-v3 import or preservation of a
  confirmed v2 installation is required. Complete encrypted v3 backups and
  previewed v3 restores remain supported requirements.
- **Compatibility/shadow/active cutover.** There is one v3 product runtime;
  the old cutover coordinator and fallback-to-v2 workflow are not delivery
  requirements. Signed v3 application/core trials, rollback and recovery remain
  required under PLAT-01 and PLAT-03.
- **USB networking, including NCM.** It is not an implementation or promotion
  dependency. USB serial seeding, diagnostics and secured-device recovery are
  not networking and are not retired by this decision.

Historical prototypes, schemas and test evidence may remain archived. Their
presence must not make these retired features prerequisites for a v3 release.
The qualification evidence contract v2 retires the migration-rollback gate;
historical counters and archived gate outcomes remain intact. Retiring the gate
does not invent a passing result or qualify any other untested gate.

## Explicit non-goals

- No USB networking implementation.
- No dynamic unsigned driver or plugin loading.
- No browser-heavy single-page application.
- No direct in-place conversion of the v2 filesystem or encrypted namespace.
- No ESP-IDF 6 selection until the chosen MicroPython baseline supports it and
  an independent platform build is qualified.
