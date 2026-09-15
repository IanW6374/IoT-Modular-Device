# Portal browser qualification

This optional host-side suite exercises the installed portal in Chromium,
Firefox, WebKit and representative mobile viewports. It never changes device
configuration or initiates an upgrade.

```sh
cd tests/browser
npm install
npm run install:browsers
IOTMD_PORTAL_URL=https://iot-md-002.example:8443 \
IOTMD_PORTAL_USERNAME=admin \
IOTMD_PORTAL_PASSWORD='your-password' npm test
```

Use a disposable qualification account where practical. The suite accepts a
locally issued HTTPS identity by design, but the production certificate chain
must be checked separately without `ignoreHTTPSErrors` during release
qualification.
