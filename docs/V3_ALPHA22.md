# IoT-MD v3.0.0-alpha.22

Alpha 22 closes the difference between automatic and manual universal upgrades.
It retains native platform ABI 6 and uses release sequence 2727.

## One universal upgrade path

- Management Suite 2.2.5 promotes the verified `.iotuni` artifact as the
  preferred signed channel entry.
- Automatic downloads stream that artifact through the existing universal
  verifier and stage the required application and core components together.
- Activation, trial health confirmation, native paired rollback and progress
  reporting are shared with manual universal uploads.
- If either installed component already has sequence 2727, its bytes are still
  verified but it is not restaged. If either component is newer, the older
  universal release is not selected.
- Signed application and core descriptors remain available for first-time setup
  and explicit recovery, but are not automatic fallbacks while a universal
  descriptor is present.

## Portal and recovery refinements

- Portal users is now under Maintenance rather than a separate top-level menu.
- Existing and new user cards align their sign-in status and initial-password
  fields, and new users can be created disabled while defaulting to enabled.
- USB application staging leaves a verified bundle ready for frozen recovery to
  activate after reset instead of prematurely creating an unconfirmed trial.

## Architecture status

All Alpha 21 greenfield mechanisms and qualification evidence remain intact.
Hardware qualification, shadow parity and controlled cutover evidence remain
the promotion gates; compatibility is still the protected rollback path.
