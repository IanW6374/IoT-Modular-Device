# IoT-MD v3.0.0-alpha.32

Alpha 32 is a focused certificate-renewal correction to the Alpha 31
qualification candidate. It retains native platform ABI 6 and uses release
sequence 2737.

IoT CA enrollment correctly persists the locally generated renewal private key
as a standard SEC1 DER key. The renewal path now decodes that representation
before producing its proof signature. It also accepts the raw P-256 scalar used
by early development builds, validates the scalar range, and continues to
report malformed key material without sending a request to IoT CA.

No re-enrollment is required. Install the application or universal Alpha 32
release, select **Renew now** under **Maintenance > Certificates > Device
certificates**, and complete the focused test in
`docs/qualification/v3.0.0-alpha.32.md` before resuming the wider campaign.

