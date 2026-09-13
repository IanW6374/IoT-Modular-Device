# IoT-MD v3.0.0-alpha.23

Alpha 23 is a focused validation successor to Alpha 22. It retains native
platform ABI 6 and uses release sequence 2728.

## Purpose

This release provides a real newer signed version with which to test the
automatic universal upgrade implementation introduced in Alpha 22. The
application, core and universal artifacts are rebuilt from one source revision
and published with provenance and an SBOM.

The Management Suite should advertise the universal artifact first. The device
should then download, verify, stage and activate the application and core using
the same paired transaction and progress workflow as a manual `.iotuni` upload.

## Functional scope

- Restart-page readiness probes abort stalled requests and continue polling,
  allowing the browser to return to sign-in automatically once the portal is
  ready.
- Authenticated pages enforce the configured per-user inactivity timeout in the
  browser and explicitly revoke the session when returning to the expired
  sign-in page.
- **Portal users** is renamed **Users**. Existing and new user forms share
  aligned field, checkbox and action geometry.
- Overview status cards reserve equal label height so wrapped and single-line
  labels retain aligned value baselines.
- **Device certificates** displays a **Renew now** action for every managed
  enrollment method and identifies the method that will be used. Manual package
  mode continues to request an explicit replacement package.
- Certificate trust cards share bottom-aligned removal actions, including the
  compact Management Suite signing-key card.
- Management Suite 2.2.6 reconciles its verified inventory with GitHub so
  upstream-deleted releases and their unreferenced local files disappear on
  the next successful synchronization.

Qualification campaign evidence remains compatible because native platform ABI
6 is unchanged; release-specific soak and health observations restart normally.
