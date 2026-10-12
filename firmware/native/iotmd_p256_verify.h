// Strict raw P-256/SHA-256 verification shared with the host C harness.
#ifndef IOTMD_P256_VERIFY_H
#define IOTMD_P256_VERIFY_H
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include "mbedtls/ecdsa.h"

static bool iotmd_p256_verify(const unsigned char *key, size_t key_length,
        const unsigned char *digest, size_t digest_length,
        const unsigned char *signature, size_t signature_length) {
    if (key_length != 64 || digest_length != 32 || signature_length != 64) {
        return false;
    }
    mbedtls_ecp_group group;
    mbedtls_ecp_point point;
    mbedtls_mpi r, s, half_order;
    mbedtls_ecp_group_init(&group);
    mbedtls_ecp_point_init(&point);
    mbedtls_mpi_init(&r);
    mbedtls_mpi_init(&s);
    mbedtls_mpi_init(&half_order);
    unsigned char encoded[65];
    encoded[0] = 4;
    memcpy(encoded + 1, key, 64);
    bool valid = false;
    if (mbedtls_ecp_group_load(&group, MBEDTLS_ECP_DP_SECP256R1) != 0 ||
            mbedtls_ecp_point_read_binary(&group, &point, encoded, sizeof(encoded)) != 0 ||
            mbedtls_ecp_check_pubkey(&group, &point) != 0 ||
            mbedtls_mpi_read_binary(&r, signature, 32) != 0 ||
            mbedtls_mpi_read_binary(&s, signature + 32, 32) != 0 ||
            mbedtls_mpi_copy(&half_order, &group.N) != 0 ||
            mbedtls_mpi_shift_r(&half_order, 1) != 0) {
        goto cleanup;
    }
    // Enforce the same low-S, nonzero and curve-order rules as the reference
    // verifier, even when this binding is called directly rather than Python.
    if (mbedtls_mpi_cmp_int(&r, 1) < 0 || mbedtls_mpi_cmp_mpi(&r, &group.N) >= 0 ||
            mbedtls_mpi_cmp_int(&s, 1) < 0 || mbedtls_mpi_cmp_mpi(&s, &half_order) > 0) {
        goto cleanup;
    }
    valid = mbedtls_ecdsa_verify(&group, digest, digest_length, &point, &r, &s) == 0;
cleanup:
    mbedtls_mpi_free(&half_order);
    mbedtls_mpi_free(&s);
    mbedtls_mpi_free(&r);
    mbedtls_ecp_point_free(&point);
    mbedtls_ecp_group_free(&group);
    return valid;
}
#endif
