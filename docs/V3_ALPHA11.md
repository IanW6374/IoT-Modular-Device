# IoT-MD v3.0.0-alpha.11 test note

## Purpose

Alpha 11 is the mixed-release and product-bootstrap hardening release. It fixes
the universal upgrade state observed in Alpha 10, where an application commit
could survive after the ESP bootloader rolled the paired core back.

## Included

- Exact paired release-sequence confirmation and restoration of the recorded
  previous application slot after a core rollback.
- Native OTA-valid readback before the paired journal becomes confirmed.
- Durable application-slot commit before native pair confirmation; if native
  confirmation fails, the recorded previous application slot is restored.
- Trial-aware application version reporting without prematurely changing the
  active-slot pointer.
- One manual-upgrade workspace with vertical steps, current-task progress,
  Cancel and a state-aware primary action.
- Simplified sign-in feedback using only the button state.
- Reboot reconciliation for the cutover journal, durable migration staging,
  v3-owned physical-resource translation and an executable product bootstrap.

## Expected behavior

During a universal trial, the overview must show the same Alpha 11 version for
the core and application. A successful health confirmation must retain both.
If either component rolls back, the other must return to the previously
confirmed release; a mixed Alpha 10/Alpha 11 pair is never a terminal outcome.

The manual upgrade card shows one workflow. The left column identifies current
and completed stages; the right column contains the file choice, current-task
progress and Cancel/primary actions. Sign-in displays `Signing in…` only once.

## Safety and rollback

The release sequence is `2716`. Install
`universal-3.0.0-alpha.11.iotuni`. Compatibility remains the default runtime and
active-v3 selection remains blocked until the Alpha 11 qualification ledger is
complete. Do not infer a passed gate from installation alone.
