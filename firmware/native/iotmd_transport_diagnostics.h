// Bounded, allocation-free telemetry. Never retain payloads or TLS identities.
#ifndef IOTMD_TRANSPORT_DIAGNOSTICS_H
#define IOTMD_TRANSPORT_DIAGNOSTICS_H

#include <stdbool.h>
#include <stdint.h>

enum {
    IOTMD_TLS_SETUP = 1,
    IOTMD_TLS_HANDSHAKE,
    IOTMD_TLS_READ,
    IOTMD_TLS_WRITE,
};

typedef struct {
    uint32_t sockets, listeners, socket_limit, socket_opens, socket_closes;
    uint32_t accepts, accept_errors, last_accept_age_ms;
    uint32_t tls_active, tls_pending, tls_opens, tls_closes, tls_errors;
    uint32_t tls_wait_ms, tls_call_ms, tls_call_stage, tls_last_progress_age_ms;
    uint32_t vm_heartbeat_age_ms, tracking_overflows;
    int32_t tls_last_error;
} iotmd_transport_snapshot_t;

void iotmd_transport_socket_open(int fd);
void iotmd_transport_socket_listen(int fd);
void iotmd_transport_socket_close(int fd);
void iotmd_transport_accept(int fd, int error);
void iotmd_transport_tls_open(const void *socket);
void iotmd_transport_tls_close(const void *socket);
void iotmd_transport_tls_enter(const void *socket, unsigned stage);
void iotmd_transport_tls_leave(const void *socket, int result, bool established, bool failed);
void iotmd_transport_heartbeat(void);
void iotmd_transport_snapshot(iotmd_transport_snapshot_t *out);

#endif
