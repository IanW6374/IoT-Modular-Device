# IoT-MD v3.0.0-alpha.84

Release sequence: 2789. Native ABI: 6. Required core API: 11.

Alpha 84 expands the mutually authenticated configuration API so Management
profiles can selectively apply the device's supported network, operational,
update, portal, API and certificate settings. Wi-Fi and MQTT passwords remain
separate encrypted secrets, while certificate and key payloads are staged and
validated through dedicated binary endpoints.

Wi-Fi SSID, DHCP and static-address changes use the existing network trial.
The device must restart and reconnect before Management confirms the new
network configuration; otherwise the retained recovery path can restore the
previous settings.

This is an application-only update and retains the Alpha 78 frozen core.
