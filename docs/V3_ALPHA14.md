# IoT-MD v3.0.0-alpha.14 test note

## Purpose

Alpha 14 applies the portal consistency feedback collected after Alpha 13. It
does not change the native ABI, signed upgrade transaction, activation order or
rollback behavior.

## Included

- Overview metrics link directly to the relevant configuration, diagnostics,
  health, upgrade or qualification page.
- Manual upgrade steps change immediately for application, core and universal
  files. The primary action is named **Upload and stage**, and the universal
  recommendation is a concise inline note.
- Installed certificate material uses a consistent green badge, expiry
  warnings use amber, and invalid or expired material uses red.
- Power-control guidance is one concise paragraph above right-aligned actions.
- Current runtime health uses the same grouped cards as persistent health data.
- Existing portal users no longer repeat the selected role in a badge.
- Shared spacing, status, action and focus treatments were reviewed across the
  authenticated portal.

## Expected behavior

Install `universal-3.0.0-alpha.14.iotuni`. Both Application version and Core
version must show `3.0.0-alpha.14` after activation and remain there after a
normal restart and power cycle. Exercise the portal checks in the matching
qualification plan before recording the release as qualified.

## Safety and rollback

The release sequence is `2719` and the native platform ABI remains 6. Alpha 14
retains Alpha 13's legacy paired-state migration and Alpha 12's native-first
confirmation, precise failure recording and power-loss recovery protections.
