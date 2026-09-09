# IoT-MD security operations

## Trust domains

Release signing, Secure Boot, flash encryption, fleet policy, portal identity,
API-client CAs, MQTT trust and release-server trust are independent. Never
reuse a private key between domains. Devices contain public verification
material; release, Secure Boot and fleet private keys remain off-device.

## Rotation

### Release signing

1. Generate and back up a replacement offline P-256 key.
2. Ship an old-key-signed transition core trusting both public keys.
3. Verify update, recovery and rollback on qualification hardware.
4. Sign the next universal release with the new key.
5. After fleet confirmation, ship a core that removes the old public key.

Never overwrite the only trusted release key without a tested USB recovery
path.

### Secure Boot

Secure Boot digest changes are eFuse operations, not ordinary OTA maintenance.
Follow the ESP-IDF revocation process only after checking remaining digest slots
on sacrificial hardware. Never revoke the last usable digest remotely.

### Fleet policy and client certificates

Back up the fleet add-on key separately. Provision a new public key, verify a
signed no-op policy and only then retire the old key. Revoke and replace
compromised API/fleet client certificates immediately.

### Service certificates

1. Issue a replacement whose DNS/IP SAN covers the exact hostname or address
   configured by every client.
2. Install the leaf, private key and required intermediate chain on the server.
3. Install or retain the issuing root in the appropriate IoT-MD trust slot;
   portal, API-client, MQTT, Syslog and release trust are separate.
4. Reload the service and inspect the identity presented on its live port.
5. Verify a real client connection with hostname and chain checking enabled
   before revoking the old certificate.

The Device API is mutual TLS: rotate its server identity independently from
the API-client certificate/CA and fingerprint registration. IoT-MD currently
uses server-authenticated TLS plus optional username/password for MQTT; it does
not present an MQTT client certificate.

## Portal accounts and sessions

Each portal user has an independent role, enabled state, failed-sign-in limit
and inactive-session timeout. Failed attempts are stored in encrypted,
transactional configuration; reaching the configured limit locks the account
until an administrator explicitly unlocks it. A successful sign-in clears the
failure counter. Keep at least two administrator accounts where operationally
appropriate so one administrator can recover another without factory reset.

Administrators can require a user to replace an administrator-issued password
at the next sign-in. The resulting session can access only logout and password
replacement until the user supplies the current password and sets a valid new
one. Successful replacement clears both the forced-change and lockout state.
Expired browser sessions discard their cookie and return to the sign-in page
with a signed-out notice; background refreshes follow the same path instead of
leaving stale status visible.

## Incident response

1. Disable automatic activation and stop rollouts.
2. Revoke affected client certificates and credentials.
3. Preserve device/add-on events, artifact hashes, SBOM and provenance.
4. Use the last known-good signed factory image and USB recovery when platform
   trust is uncertain.
5. Rotate Wi-Fi, MQTT and portal credentials independently.
