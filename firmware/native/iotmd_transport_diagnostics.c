// Native timer telemetry continues even if MicroPython's event loop stalls.
// Fixed-size records contain only socket handles, counters, stages and times.
#include <string.h>
#include <inttypes.h>
#include "iotmd_transport_diagnostics.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "sdkconfig.h"

#define SOCKET_RECORDS (CONFIG_LWIP_MAX_SOCKETS)
#define TLS_RECORDS (CONFIG_LWIP_MAX_SOCKETS + 2)

typedef struct {
    bool used, listening;
    int fd;
} socket_record_t;

typedef struct {
    const void *socket;
    bool established;
    uint32_t opened_ms, call_started_ms;
    unsigned stage;
} tls_record_t;

static socket_record_t sockets[SOCKET_RECORDS];
static tls_record_t tls[TLS_RECORDS];
static iotmd_transport_snapshot_t counters;
static uint32_t heartbeat_ms, last_accept_ms, last_progress_ms, last_report_ms;
static bool heartbeat_seen, accept_seen, progress_seen;
static esp_timer_handle_t timer;
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;

static uint32_t now_ms(void) {
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static tls_record_t *find_tls(const void *socket) {
    for (unsigned i = 0; i < TLS_RECORDS; ++i) {
        if (tls[i].socket == socket) {
            return &tls[i];
        }
    }
    return NULL;
}

void iotmd_transport_socket_open(int fd) {
    if (fd < 0) {
        return;
    }
    portENTER_CRITICAL(&lock);
    for (unsigned i = 0; i < SOCKET_RECORDS; ++i) {
        if (sockets[i].used && sockets[i].fd == fd) {
            portEXIT_CRITICAL(&lock);
            return;
        }
    }
    ++counters.socket_opens;
    for (unsigned i = 0; i < SOCKET_RECORDS; ++i) {
        if (!sockets[i].used) {
            sockets[i] = (socket_record_t){.used = true, .fd = fd};
            portEXIT_CRITICAL(&lock);
            return;
        }
    }
    ++counters.tracking_overflows;
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_socket_listen(int fd) {
    portENTER_CRITICAL(&lock);
    for (unsigned i = 0; i < SOCKET_RECORDS; ++i) {
        if (sockets[i].used && sockets[i].fd == fd) {
            sockets[i].listening = true;
        }
    }
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_socket_close(int fd) {
    portENTER_CRITICAL(&lock);
    for (unsigned i = 0; i < SOCKET_RECORDS; ++i) {
        if (sockets[i].used && sockets[i].fd == fd) {
            memset(&sockets[i], 0, sizeof(sockets[i]));
            ++counters.socket_closes;
            break;
        }
    }
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_accept(int fd, int error) {
    uint32_t now = now_ms();
    portENTER_CRITICAL(&lock);
    if (fd >= 0) {
        ++counters.accepts;
        last_accept_ms = now;
        accept_seen = true;
    } else if (error) {
        ++counters.accept_errors;
    }
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_tls_open(const void *socket) {
    uint32_t now = now_ms();
    portENTER_CRITICAL(&lock);
    if (find_tls(socket)) {
        portEXIT_CRITICAL(&lock);
        return;
    }
    ++counters.tls_opens;
    for (unsigned i = 0; i < TLS_RECORDS; ++i) {
        if (!tls[i].socket) {
            tls[i] = (tls_record_t){.socket = socket, .opened_ms = now};
            portEXIT_CRITICAL(&lock);
            return;
        }
    }
    ++counters.tracking_overflows;
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_tls_close(const void *socket) {
    portENTER_CRITICAL(&lock);
    tls_record_t *record = find_tls(socket);
    if (record) {
        memset(record, 0, sizeof(*record));
        ++counters.tls_closes;
    }
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_tls_enter(const void *socket, unsigned stage) {
    uint32_t now = now_ms();
    portENTER_CRITICAL(&lock);
    tls_record_t *record = find_tls(socket);
    if (record) {
        record->stage = stage;
        record->call_started_ms = now;
    }
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_tls_leave(const void *socket, int result, bool established, bool failed) {
    uint32_t now = now_ms();
    portENTER_CRITICAL(&lock);
    tls_record_t *record = find_tls(socket);
    if (record) {
        record->stage = 0;
        if (established && !record->established) {
            record->established = true;
            last_progress_ms = now;
            progress_seen = true;
        }
        if (result > 0) {
            last_progress_ms = now;
            progress_seen = true;
        }
    }
    if (failed) {
        ++counters.tls_errors;
        counters.tls_last_error = result;
    }
    portEXIT_CRITICAL(&lock);
}

void iotmd_transport_snapshot(iotmd_transport_snapshot_t *out) {
    uint32_t now = now_ms();
    portENTER_CRITICAL(&lock);
    *out = counters;
    out->socket_limit = SOCKET_RECORDS;
    out->vm_heartbeat_age_ms = heartbeat_seen ? now - heartbeat_ms : 0;
    out->last_accept_age_ms = accept_seen ? now - last_accept_ms : 0;
    out->tls_last_progress_age_ms = progress_seen ? now - last_progress_ms : 0;
    for (unsigned i = 0; i < SOCKET_RECORDS; ++i) {
        out->sockets += sockets[i].used;
        out->listeners += sockets[i].used && sockets[i].listening;
    }
    for (unsigned i = 0; i < TLS_RECORDS; ++i) {
        if (!tls[i].socket) {
            continue;
        }
        ++out->tls_active;
        if (!tls[i].established) {
            ++out->tls_pending;
            uint32_t age = now - tls[i].opened_ms;
            if (age > out->tls_wait_ms) {
                out->tls_wait_ms = age;
            }
        }
        if (tls[i].stage) {
            uint32_t age = now - tls[i].call_started_ms;
            if (age >= out->tls_call_ms) {
                out->tls_call_ms = age;
                out->tls_call_stage = tls[i].stage;
            }
        }
    }
    portEXIT_CRITICAL(&lock);
}

static void report_timer(void *unused) {
    (void)unused;
    uint32_t now = now_ms();
    iotmd_transport_snapshot_t state;
    iotmd_transport_snapshot(&state);
    if (!state.listeners) {
        // Intentional listener shutdown is not an event-loop failure.
        return;
    }
    const uint32_t caps = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;
    uint32_t largest = heap_caps_get_largest_free_block(caps);
    bool warning = state.vm_heartbeat_age_ms >= 15000 ||
        state.tls_call_ms >= 10000 || state.tls_wait_ms >= 30000 ||
        largest < 4096;
    if ((uint32_t)(now - last_report_ms) < (warning ? 30000 : 60000)) {
        return;
    }
    last_report_ms = now;
    // Native UART only: no Python callback, socket, GC, or payload formatting.
    ESP_LOG_LEVEL(warning ? ESP_LOG_WARN : ESP_LOG_INFO, "IoT-MD-Transport",
        "vm_age_ms=%"PRIu32" sockets=%"PRIu32"/%"PRIu32
        " listeners=%"PRIu32" accepts=%"PRIu32" accept_age_ms=%"PRIu32
        " tls=%"PRIu32" pending=%"PRIu32" wait_ms=%"PRIu32
        " call_stage=%"PRIu32" call_ms=%"PRIu32" progress_age_ms=%"PRIu32
        " tls_errors=%"PRIu32" last_error=%"PRId32
        " internal_free=%u internal_largest=%"PRIu32" internal_min=%u overflow=%"PRIu32,
        state.vm_heartbeat_age_ms, state.sockets, state.socket_limit,
        state.listeners, state.accepts, state.last_accept_age_ms,
        state.tls_active, state.tls_pending, state.tls_wait_ms,
        state.tls_call_stage, state.tls_call_ms, state.tls_last_progress_age_ms,
        state.tls_errors, state.tls_last_error,
        (unsigned)heap_caps_get_free_size(caps), largest,
        (unsigned)heap_caps_get_minimum_free_size(caps), state.tracking_overflows);
}

void iotmd_transport_heartbeat(void) {
    uint32_t now = now_ms();
    portENTER_CRITICAL(&lock);
    heartbeat_ms = now;
    heartbeat_seen = true;
    portEXIT_CRITICAL(&lock);
    if (!timer) {
        const esp_timer_create_args_t args = {
            .callback = report_timer, .name = "iotmd-transport",
            .skip_unhandled_events = true,
        };
        if (esp_timer_create(&args, &timer) == ESP_OK) {
            if (esp_timer_start_periodic(timer, 10000000) != ESP_OK) {
                esp_timer_delete(timer);
                timer = NULL;
            }
        }
    }
}
