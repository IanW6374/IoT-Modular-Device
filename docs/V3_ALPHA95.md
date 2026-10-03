# IoT-MD v3.0.0-alpha.95

Alpha 95 prevents centrally managed encrypted backup creation and preview from
blocking the device event loop during password-key derivation.

- Product version: `3.0.0-alpha.95`
- Release sequence: `2800`
- Application runtime generation: `192`
- Required core API: `12`

Management derives the backup key on the Home Assistant host and transfers the
single-use derived key over mutual TLS. The encrypted backup envelope remains
at format version 2, so existing recovery points and local password-based
backup and restore operations remain compatible.
