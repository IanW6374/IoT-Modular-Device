// Opt-in native allocation tracing. No payloads, credentials or Python objects.
#include "sdkconfig.h"
#include "iotmd_heap_diagnostics.h"

#if CONFIG_HEAP_TRACING_STANDALONE
#include <inttypes.h>
#include <string.h>
#include "esp_heap_caps.h"
#include "esp_heap_trace.h"
#include "esp_memory_utils.h"
#include "esp_log.h"
#include "esp_timer.h"

#if CONFIG_HEAP_TRACING_STACK_DEPTH != 6
#error "IoT-MD heap diagnostics require the six-frame tracing configuration"
#endif

#define TRACE_RECORDS 2048
#define TRACE_GROUPS 32
#define TRACE_WARMUP_MS 90000U
#define TRACE_CAPTURE_MS 120000U
#define TRACE_DRAIN_MS 45000U
#define TRACE_INTERVAL_MS 600000U
#define TRACE_WINDOWS 3U

typedef struct {
    void *callers[CONFIG_HEAP_TRACING_STACK_DEPTH];
    size_t count, bytes;
} allocation_group_t;

static const char tag[] = "IoT-MD-Heap";
static heap_trace_record_t *records;
static allocation_group_t groups[TRACE_GROUPS];
static enum { WARMUP, CAPTURE, DRAIN, BETWEEN, FINISHED } phase;
static bool initialized;
static unsigned windows;
static uint32_t phase_started;
static size_t free_at_start;

static void report(void) {
    memset(groups, 0, sizeof(groups));
    heap_trace_summary_t summary = {0};
    heap_trace_summary(&summary);
    size_t internal_count = 0, internal_bytes = 0;
    size_t omitted_count = 0, omitted_bytes = 0;
    unsigned group_count = 0;
    for (size_t i = 0; i < summary.count; ++i) {
        heap_trace_record_t record;
        if (heap_trace_get(i, &record) != ESP_OK || record.freed ||
            !record.address || !esp_ptr_internal(record.address)) {
            continue;
        }
        ++internal_count;
        internal_bytes += record.size;
        unsigned g;
        for (g = 0; g < group_count; ++g) {
            if (!memcmp(groups[g].callers, record.alloced_by,
                sizeof(groups[g].callers))) {
                break;
            }
        }
        if (g == group_count) {
            if (group_count == TRACE_GROUPS) {
                ++omitted_count;
                omitted_bytes += record.size;
                continue;
            }
            memcpy(groups[g].callers, record.alloced_by,
                sizeof(groups[g].callers));
            ++group_count;
        }
        ++groups[g].count;
        groups[g].bytes += record.size;
    }
    ESP_LOGI(tag, "window=%u capture_ms=%u drain_ms=%u retained_internal=%u"
        " bytes=%u free_start=%u free_end=%u peak=%u capacity=%u overflow=%u"
        " omitted_count=%u omitted_bytes=%u isr_excluded=1",
        windows, TRACE_CAPTURE_MS, TRACE_DRAIN_MS, (unsigned)internal_count,
        (unsigned)internal_bytes, (unsigned)free_at_start,
        (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT),
        (unsigned)summary.high_water_mark, (unsigned)summary.capacity,
        (unsigned)summary.has_overflowed, (unsigned)omitted_count,
        (unsigned)omitted_bytes);
    // Sort largest retained allocation groups first; report at most 32 lines.
    for (unsigned i = 0; i < group_count; ++i) {
        unsigned biggest = i;
        for (unsigned j = i + 1; j < group_count; ++j) {
            if (groups[j].bytes > groups[biggest].bytes) {
                biggest = j;
            }
        }
        allocation_group_t swap = groups[i];
        groups[i] = groups[biggest];
        groups[biggest] = swap;
        // Stack depth is pinned to six in sdkconfig.heap-trace.
        ESP_LOGI(tag, "window=%u retained=%u bytes=%u pcs=%p,%p,%p,%p,%p,%p",
            windows, (unsigned)groups[i].count, (unsigned)groups[i].bytes,
            groups[i].callers[0], groups[i].callers[1], groups[i].callers[2],
            groups[i].callers[3], groups[i].callers[4], groups[i].callers[5]);
    }
}

static void finish(void) {
    // Detach before releasing the PSRAM buffer; never free an active trace.
    if (heap_trace_init_standalone(NULL, 0) == ESP_OK) {
        heap_caps_free(records);
        records = NULL;
    }
    phase = FINISHED;
}

void iotmd_heap_diagnostics_poll(void) {
    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
    if (!initialized) {
        initialized = true;
        phase_started = now;
        esp_log_level_set(tag, ESP_LOG_INFO);
        ESP_LOGI(tag, "enabled warmup_ms=%u windows=%u records=%u stack_depth=%u",
            TRACE_WARMUP_MS, TRACE_WINDOWS, TRACE_RECORDS,
            CONFIG_HEAP_TRACING_STACK_DEPTH);
        return;
    }
    uint32_t elapsed = now - phase_started; // Safe across tick wrap.
    switch (phase) {
        case WARMUP:
        case BETWEEN:
            if (elapsed < (phase == WARMUP ? TRACE_WARMUP_MS : TRACE_INTERVAL_MS)) {
                return;
            }
            if (!records) {
                // Diagnostic storage must not consume the internal heap under investigation.
                records = heap_caps_calloc(TRACE_RECORDS, sizeof(*records),
                    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
                if (!records || heap_trace_init_standalone(records, TRACE_RECORDS) != ESP_OK) {
                    heap_caps_free(records);
                    records = NULL;
                    phase = FINISHED;
                    ESP_LOGE(tag, "trace initialization failed; tracing disabled");
                    return;
                }
            }
            free_at_start = heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
            if (heap_trace_start(HEAP_TRACE_LEAKS) != ESP_OK) {
                ESP_LOGE(tag, "trace start failed; tracing disabled");
                finish();
                return;
            }
            ++windows;
            phase = CAPTURE;
            phase_started = now;
            ESP_LOGI(tag, "window=%u capture started", windows);
            return;
        case CAPTURE:
            if (elapsed < TRACE_CAPTURE_MS) {
                return;
            }
            if (heap_trace_alloc_pause() != ESP_OK) {
                heap_trace_stop();
                ESP_LOGE(tag, "trace pause failed; tracing disabled");
                finish();
                return;
            }
            phase = DRAIN;
            phase_started = now;
            return;
        case DRAIN:
            if (elapsed < TRACE_DRAIN_MS) {
                return;
            }
            if (heap_trace_stop() != ESP_OK) {
                // Do not detach/free a buffer if tracing could still be active.
                phase = FINISHED;
                ESP_LOGE(tag, "trace stop failed; buffer retained for safety");
                return;
            }
            report();
            if (windows == TRACE_WINDOWS) {
                finish();
            } else {
                phase = BETWEEN;
                phase_started = now;
            }
            return;
        case FINISHED:
            return;
    }
}
#else
void iotmd_heap_diagnostics_poll(void) {}
#endif
