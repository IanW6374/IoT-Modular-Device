#pragma once

// Called by the existing frozen-core heartbeat, never from the ESP timer/ISR.
// A normal build compiles this to a no-op; --heap-trace enables bounded runs.
void iotmd_heap_diagnostics_poll(void);
