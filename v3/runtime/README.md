# MicroPython application runtime

The runtime owns product behavior:

- configuration validation, migration and policy;
- service composition, task supervision and health interpretation;
- module discovery, resource requests, drivers, state and commands;
- MQTT, Home Assistant, portal and Device API behavior;
- certificate enrollment policy and renewal orchestration;
- fleet, audit, support and operational diagnostics; and
- transport-neutral request, response and event models.

Alpha 14 consumes native platform ABI 6 and configuration contract version 4.
It normalises activating state created by pre-ABI-6 frozen coordinators before
the runtime drives the native paired journal through opaque primitive calls,
marks the expected runtime slot healthy before native confirmation and leaves
the durable pointer on the prior slot until that confirmation succeeds. A failed
native trial can therefore be discarded entirely by frozen recovery, including
after a bootloader rollback to an older core. A product bootstrap owns the
single production composition root, while interrupted cutover startup is
durably latched to compatibility. Migration handle intents survive restart and
the production driver translator is independent of v2 implementation modules.
Shadow mode validates and compares only; it cannot bind listeners, publish MQTT
state or construct physical resources.

Alpha 9 introduced physical and production adapter integration. Module resource
declarations carry bounded physical parameters and explicit
shared-bus signatures. Production lifecycle bridges adapt Wi-Fi, MQTT, HTTPS,
mTLS Device API and syslog implementations to the transport-independent v3
services. The identity bridge reads the installed certificate inventory,
persists stable opaque certificate/key handles in encrypted transactional NVS,
dispatches every managed enrollment/renewal method and generation-guards trust
removal. Paths and key material never appear in the identity contract.

Alpha 7 introduced the frozen boot supervisor, which advances a
native boot record before importing replaceable product code and can enter the
existing signed recovery path after an explicit request or three incomplete
boots. The runtime can observe and guard OTA trial operations, submit bounded
native recovery/update jobs and consume structured completion events without
exposing partitions, NVS objects or FreeRTOS handles.

Alpha 6 added a persistent operational qualification service and the
compatibility/shadow/active cutover coordinator. Active ownership is refused
unless native paired trial and rollback capabilities are available and all 15
qualification gates contain passing observed evidence. A v3 boot or health
failure requests recovery and returns to compatibility mode. Alpha 5's
declarative identity and fleet services, opaque certificate and
migration handles, signed policy/canary reporting, previewed v2 backup
migration and the complete v2.5 driver catalog over multi-resource claims
remain in place.
Alpha 4's bounded Wi-Fi/MQTT/portal/mTLS API services, shared portal metadata
and unified connectivity diagnostics remain transport adapters around those
domains. Alpha 3's service registry, resource adapter, reference sensor and
bounded kernel snapshots remain the composition base. Alpha 2's fail-closed
transactional-storage and paired-release adapters remain in place. The paired
coordinator can now reconcile the native ABI 6 journal, but native paired-trial
and rollback qualification claims remain false until the hardware
power-interruption campaign passes.

Runtime code consumes only the versioned platform ABI. It may request a
platform operation but cannot access partitions, raw encrypted storage, native
network handles or key bytes. Services depend on domain contracts; HTTP, MQTT,
display and future USB transports are adapters.

The portal remains server-rendered with bounded enhancement JavaScript. Form
metadata and navigation are declarative so first-boot and maintenance pages
reuse validation, labels and help text.
