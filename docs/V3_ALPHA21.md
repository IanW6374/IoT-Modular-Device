# IoT-MD v3.0.0-alpha.21

Alpha 21 repairs an Alpha 20 compact-build portal dispatcher defect and makes
automatic paired upgrades explicit throughout the portal. It retains native
platform ABI 6 and release sequence 2726.

## Portal release repair

- The application release builder now passes every captured request, session
  and user-management dependency into the independently compiled portal route
  modules.
- A source-level contract test compares each extracted dispatcher's captured
  variables with its generated arguments, preventing source tests from passing
  when packaged MicroPython code would contain an undefined name.
- The repair covers the observed `action_path` and `cookie_session_id` failures
  plus latent session, header and portal-user dependencies found by the same
  audit.

## Upgrade presentation

- Automatic two-component releases are labelled **Paired upgrade (core +
  application)** instead of exposing only the currently active component.
- Individual offers use explicit Application, Core firmware or Universal
  upgrade labels.
- **Download and stage** accurately describes the signed download, verification
  and staging operation and remains right-aligned beside the release details.
- Once an artifact is staged, the common state is shown under **Upgrade
  process** rather than appearing to move an automatic release into Manual
  upgrade.

## Architecture status

All Alpha 20 greenfield mechanisms and qualification evidence remain intact.
Hardware qualification, shadow parity and controlled cutover evidence remain
the promotion gates; compatibility is still the protected rollback path.
