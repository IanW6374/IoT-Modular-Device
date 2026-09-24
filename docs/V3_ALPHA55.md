# IoT-MD v3.0.0-alpha.55

Release sequence: 2760. Native ABI: 6. MicroPython: 1.29.0. ESP-IDF: 5.5.5.

Alpha 55 is a signed application-only dummy release for testing Alpha 54's
discard-and-retry correction. It contains no intentional functional changes
beyond the product and runtime version increment and remains compatible with
the Alpha 52 native core.

Install Alpha 54 first so its corrected updater is running. Begin staging
Alpha 55, select **Discard** during verification, and then stage the same Alpha
55 bundle again. The second attempt must remain on the staged workflow with an
active **Restart and install** control.
