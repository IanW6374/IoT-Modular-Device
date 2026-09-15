# IoT-MD v3.0.0-alpha.33

Alpha 33 completes the unified upgrade-workflow presentation. It retains native
platform ABI 6 and uses release sequence 2738.

Automatic and Manual are now explicit choices inside one installation flow.
Manual upgrades request a local signed file; Automatic upgrades offer the
newer, compatible versions authenticated from the selected Management Suite
channel. The newest valid version remains selected by default, and the server
rejects any submitted version that was not present in the checked inventory.

The workflow uses a horizontal milestone track with the task name above each
circle, a circular percentage for each stage and a compact vertical layout on
narrow screens. Selecting an automatic version changes the displayed stages to
match its universal, application or core artifact type.

Management Suite 2.2.7 publishes the bounded multi-version inventory while
retaining `latest.json` for older devices. Alpha 33 also falls back to that
single-release catalog when used with an earlier Management Suite.

