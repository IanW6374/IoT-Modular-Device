# IoT-MD v3.0.0-alpha.96

Alpha 96 adds a migration guard for the managed-backup responsiveness change
introduced in Alpha 95.

- Product version: `3.0.0-alpha.96`
- Release sequence: `2801`
- Application runtime generation: `193`
- Required core API: `12`

Remote password-only backup requests from Management versions older than 2.7.3
are rejected immediately instead of performing PBKDF2 on the device event loop.
Local portal backups retain the password-based workflow, and Management 2.7.3
uses the non-blocking derived-key API.
