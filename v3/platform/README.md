# Native ESP-IDF platform

The platform is a purpose-built ESP-IDF application which embeds the qualified
MicroPython runtime. It owns mechanisms that must remain available when the
replaceable application is absent or broken:

- secure boot, flash encryption and hardware identity;
- watchdog, reset reason, boot stages and recovery selection;
- encrypted NVS, credential handles and filesystem mounting;
- OTA partition selection, signed staging, trial confirmation and rollback;
- Wi-Fi, native USB and future Ethernet interface drivers;
- monotonic time, heap/PSRAM, flash and hardware-resource observations; and
- the bounded `_iotmd_platform` ABI exposed to MicroPython.

Platform code must not know about portal routes, MQTT topics, Home Assistant,
fleet policy, module semantics or presentation. Native operations which can
block are represented as jobs and publish completion through the platform event
queue. Secret key material is referred to by opaque handles and is never
returned to MicroPython.

ABI 6 retains ABI 5's physical resource lifecycle, encrypted native
boot/recovery state and fixed four-job/eight-event worker, and adds an encrypted
paired-release journal. The journal binds the monotonic release sequence, pair
identifier, running platform partition, trial runtime slot and previous runtime
slot. Runtime health must be marked for that exact pair before guarded native
OTA confirmation is possible. Rollback intent is persisted before the previous
runtime is restored and bootloader rollback is requested.

ABI 5 turned logical resource claims into
physical peripheral lifecycles. The native platform constructs GPIO, ADC,
UART, I2C and SPI resources, shares only identically configured I2C/SPI buses,
removes GPIO interrupt handlers during cleanup, and can rebuild a failed
peripheral or clear stale claims after a MicroPython restart without exposing an
ESP-IDF handle to MicroPython. Interrupts enter
the same bounded event queue and never block the ISR. Resource qualification
remains false until the board/driver HIL matrix passes. Paired trial, rollback,
recovery and job qualification likewise remain false pending their own HIL
gates. Recovery is independent of replaceable product code; it still relies on
the signed frozen MicroPython core. ABI 6 does not claim bare-ESP-IDF recovery
from a corrupt confirmed core.
