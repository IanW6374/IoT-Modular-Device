# IoT-MD v3.0.0-alpha.90

Release sequence: 2795. Native ABI: 6. Required runtime core API: 12.

Alpha 90 fixes Management Suite recovery-point previews on devices whose
retained native core still supplies the earlier general Device API request
limit. The application API now applies a bounded 384 KiB allowance only to the
complete-backup preview route. Other API routes retain the configured lower
limit.
