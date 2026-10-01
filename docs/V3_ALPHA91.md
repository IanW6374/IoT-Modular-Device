# IoT-MD v3.0.0-alpha.91

Release sequence: 2796. Native ABI: 6. Required runtime core API: 12.

Alpha 91 establishes the V3-only application baseline now that every managed
device runs V3. Application bundles no longer include the retired V2 migration,
shadow, cutover, bootstrap or compatibility coordinators. Native platform,
encrypted qualification storage and operational qualification remain included.

The native adapter package no longer imports every historical prototype during
package initialization, and the structured event sink no longer exposes V2
compatibility naming. The stable `/api/v2` URL remains unchanged because it is
the Device API contract version, not a firmware-generation hook.
