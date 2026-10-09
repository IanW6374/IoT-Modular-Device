# Certificate identities and provisioning

From Alpha 110, IoT-MD presents one HTTPS certificate/key on portal and API.
Use the same canonical DNS hostname for both ports (portal 8443, API 8444 by
default). The .local mDNS name is only a discovery alias. Configure Management
with the HTTPS name covered by the certificate SAN; DNS must resolve it.

| Purpose | Identity or trust | Issuer |
| --- | --- | --- |
| Portal and API HTTPS | web.crt.pem / web.key.der | Public ACME, private CA, self-signed or manual |
| API callers | API client CAs and enrolled caller certificates | Private IoT CA |
| Renewal caller | Device-generated renewal key/certificate | Private IoT CA |
| MQTT, release, Syslog servers | Corresponding outbound CA trust anchors | Remote server's issuing CA |
| Management authorization | Management policy and catalog verification key | Management signing identity |

Sharing server identity does not share authentication. Portal access uses the
administrator login. API access always requires mTLS, an enrolled client
fingerprint and permission scopes. Publicly issuing the server certificate
does not allow anonymous API access. Outbound service trust remains separate.

## TLS names and chains

Trusted issuance and matching DNS/IP SANs are both required. A matching Common
Name cannot override a mismatched SAN. Servers must present the leaf and required
intermediates; trusting a root does not repair a missing intermediate. Never
disable certificate verification. Management trusts its configured private root
and system public roots while still supplying its private client certificate.
Open portal uses the device's advertised HTTPS hostname, not its discovery alias.

## First-run certificate choices

1. Automatic IoT CA enrollment: shared HTTPS identity through a time-limited
   trusted-LAN enrollment window.
2. IoT CA authorization (.iotenroll): the same identity from a one-time,
   hostname-bound authorization downloaded by an administrator.
3. Private CA ACME: local DNS name with HTTP-01 against the private IoT CA.
4. Manual certificate package: shared HTTPS chain/key and private IoT root.
5. Self-signed certificate: the device-generated local fallback; clients must
   explicitly trust it. No certificate files are required for this choice.

No route is silently applied. Only the selected route's controls are displayed.

## Device / Settings / Certificates

- Certificate enrollment shows the method, renewal behaviour and replacement
  controls. Certificate/key installation is validated and committed atomically.
- Device certificates shows the single Device HTTPS identity (portal and API).
  Renew now invokes the active managed method.
- API client trust manages issuer CAs, registered callers and scopes. Standard,
  Management Suite, Qualification automation and Custom presets remain available.
  Edit API scopes updates an existing caller; profile writes require
  configuration:write. Revoking a caller does not change the server identity.
- CA & signing trust manages outbound service CAs and the Management policy and
  catalog verification key. Removing trust prevents the corresponding service
  from authenticating until replacement trust is installed.

The Management verification key is a public signing key, not an X.509 CA or a
private key on the device. It authorizes policies, commands and format-3 catalogs.
Update artifacts are independently verified by the immutable offline update key.
Secure boot and flash encryption do not replace caller authorization/signatures.

## Enrollment and renewal

Use Certificate Authority 0.6.0 with Alpha 110. Enrollment/renewal protocol v2
accepts only HTTPS-server and renewal-client CSRs. Existing protocol-v1 managed
devices must re-enroll through Certificate enrollment. No split-identity
compatibility or migration path is provided. Updating firmware does not erase
configuration or API caller trust.

Configure a resolvable IoT CA name (iot-ca.home.arpa by default) and mapped
provisioning port (9010 by default). Open the time-limited enrollment window in
CA Overview. This bootstrap route is disabled by default, private-LAN restricted,
rate-limited and audited. The returned authorization pins subsequent traffic to
the private root. On an untrusted setup LAN, download .iotenroll instead. It
expires after 30 minutes and cannot be claimed with different certificate requests.

The authorization binds the discovery name and canonical HTTPS hostname. The
device creates independent P-256 HTTPS and renewal-client keys locally and sends
only signed CSRs over pinned HTTPS. CA validates exact names/usages, performs
Cloudflare DNS-01 for the HTTPS CSR and privately signs the renewal CSR. Only
certificates and public trust are returned; private keys and Cloudflare credentials
never leave their owner.

The private renewal credential authorizes rotating these two certificates after
two-thirds of the HTTPS lifetime. It is not a second API server identity.
Renewal reloads both listeners without rebooting. Private ACME and self-signed
routes also renew the shared identity; manual packages need explicit replacement.

## Manual public provisioning

Issue a device public certificate package in CA 0.6.0, unzip on the administrator
workstation and select the private IoT root, canonical HTTPS DNS hostname,
web.crt.pem (leaf and intermediate chain) and web.key.der in first-run setup.
There are no api-server.* files. Validate one key pair before committing.
Complete encrypted backups contain the shared identity once; restore validates
its certificate/key pair before activation. No provisioning route gives a device
DNS-edit credentials.
