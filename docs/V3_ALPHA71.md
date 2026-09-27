# IoT-MD v3.0.0-alpha.71

Release sequence: 2776. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 71 fixes the fleet inventory failure seen on Alpha 69 and Alpha 70. The
active Management Suite key fingerprint is now calculated by an
application-owned module included in the update bundle, rather than by a new
function on the retained native-core `update_security` module.

Automatic updates now follow the same in-place interaction model as Manual
updates. Starting an Automatic update retains the Updates page, updates the
existing progress graph while the background task runs, and replaces that
workspace with the staged restart control when verification completes. The
standalone task URL remains available as a non-JavaScript fallback.

Because Alpha 69 and Alpha 70 cannot report the active fleet key, install
Alpha 71 once through the Manual update method. IoT-MD Management Suite 2.2.20
can then refresh and compare the active device fingerprint before signing a
deployment.
