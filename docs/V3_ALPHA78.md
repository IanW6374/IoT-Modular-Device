# IoT-MD v3.0.0-alpha.78

Release sequence: 2783. Native ABI: 6. Core API: 11. MicroPython: 1.29.0.
ESP-IDF: 5.5.5.

Alpha 78 is a matched universal application and core release. The frozen
supervisor now commits the A/B application trial when the replaceable runtime
reaches its local health marker. This closes a boundary where a healthy trial
could reach network, portal, services and running state while the supervisor
still retained `trial` and subsequently rolled it back.

Install the `.iotuni` artifact locally before testing another managed
application deployment.
