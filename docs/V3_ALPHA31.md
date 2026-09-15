# IoT-MD v3.0.0-alpha.31

Alpha 31 is the final planned implementation alpha before the full greenfield
qualification campaign. It retains native platform ABI 6 and uses release
sequence 2736. Passing host tests or installing this release does not itself
close any hardware qualification gate.

## Resilient portal operations

Manual upgrade chunks now continue from network-completion callbacks and no
longer depend on animation frames, which browsers suspend in background tabs.
The device owns asynchronous release and certificate operation state in a
bounded task registry. Stable task URLs, page refresh and the global running
task indicator can therefore reconnect to in-progress work without restarting
it. Live pages resynchronise immediately when made visible and poll less often
while hidden.

Local file transfer and unsaved forms warn before navigation. Operation pages
show their latest device check time, failures link to a filtered Device log and
Overview identifies its most recent refresh.

## Accessibility, presentation and browser coverage

The shell now has skip navigation, an explicit main landmark, keyboard movement
through both menu levels, consistent visible focus and minimum target sizing.
It honours reduced-motion, dark-colour and forced-colour operating-system
preferences without adding a device setting.

A host-side Playwright and axe suite covers Chromium, Firefox, WebKit, Pixel 5
and iPhone 13 profiles. It is deliberately non-destructive and requires an
installed device plus a disposable qualification login. See
`tests/browser/README.md`.

## Security and efficiency

Each HTML response receives a unique script/style nonce and a strict Content
Security Policy. HTTPS sessions use a `__Host-` cookie with Secure, HttpOnly and
SameSite Strict attributes. Fingerprinted CSS and JavaScript retain immutable
caching and now support strong ETag revalidation.

HSTS is intentionally not enabled during alpha qualification: devices can use
local or self-signed identities and an unconditional browser pin could make
recovery harder after a certificate or hostname change. Enablement remains a
deployment policy decision after the production hostname and trust chain are
qualified.

The portal remains server-rendered and dependency-light. A SPA, PWA service
worker, WebSocket transport and duplicated pre-compressed assets were excluded
because their flash, memory and recovery complexity do not improve this
low-concurrency device workflow.

## Exit from alpha

No further feature or architectural work is planned before qualification.
Promotion still requires the native paired-update, independent-recovery,
resource/driver, transport, identity, fleet/migration, shadow/cutover and
operational soak evidence defined in the roadmap and release qualification
record.
