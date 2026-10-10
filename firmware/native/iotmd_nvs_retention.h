// Reclaim only strictly older, fully verified transaction generations.
// The selected generation (including API replay watermarks) is never erased.
#ifndef IOTMD_NVS_RETENTION_H
#define IOTMD_NVS_RETENTION_H

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "nvs.h"

static uint32_t iotmd_nvs_u32(const uint8_t *value) {
    return (uint32_t)value[0] | ((uint32_t)value[1] << 8) |
        ((uint32_t)value[2] << 16) | ((uint32_t)value[3] << 24);
}

static uint32_t iotmd_nvs_crc32(const uint8_t *value, size_t length) {
    uint32_t crc = 0xffffffff;
    for (size_t index = 0; index < length; ++index) {
        crc ^= value[index];
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ (0xedb88320 & (0 - (crc & 1)));
        }
    }
    return ~crc;
}

static esp_err_t iotmd_nvs_snapshot_generation(nvs_handle_t nvs,
        const char *key, uint32_t *generation) {
    size_t length = 0;
    esp_err_t error = nvs_get_blob(nvs, key, NULL, &length);
    if (error != ESP_OK) { return error; }
    if (length < 16 || length > 16 + 4096) {
        return ESP_ERR_INVALID_STATE;
    }
    uint8_t *buffer = malloc(length);
    if (buffer == NULL) { return ESP_ERR_NO_MEM; }
    size_t actual = length;
    error = nvs_get_blob(nvs, key, buffer, &actual);
    if (error == ESP_OK && (actual != length ||
            memcmp(buffer, "I3TX", 4) != 0 ||
            iotmd_nvs_u32(buffer + 8) != length - 16 ||
            iotmd_nvs_crc32(buffer + 16, length - 16) !=
                iotmd_nvs_u32(buffer + 12))) {
        error = ESP_ERR_INVALID_STATE;
    }
    if (error == ESP_OK) {
        *generation = iotmd_nvs_u32(buffer + 4);
        if (*generation == 0 ||
                (strcmp(key, "snapshot_a") == 0 && (*generation & 1)) ||
                (strcmp(key, "snapshot_b") == 0 && !(*generation & 1))) {
            error = ESP_ERR_INVALID_STATE;
        }
    }
    memset(buffer, 0, length);
    free(buffer);
    return error;
}

static esp_err_t iotmd_nvs_reclaim_snapshot(nvs_handle_t nvs) {
    uint32_t a = 0, b = 0;
    esp_err_t error_a = iotmd_nvs_snapshot_generation(nvs, "snapshot_a", &a);
    esp_err_t error_b = iotmd_nvs_snapshot_generation(nvs, "snapshot_b", &b);
    // Missing slots are normal; corruption or read failures are not permission
    // to choose an older state or delete any evidence of a newer watermark.
    if (error_a != ESP_OK && error_a != ESP_ERR_NVS_NOT_FOUND) { return error_a; }
    if (error_b != ESP_OK && error_b != ESP_ERR_NVS_NOT_FOUND) { return error_b; }
    if (error_a != ESP_OK || error_b != ESP_OK) { return ESP_OK; }
    if (a == b) { return ESP_ERR_INVALID_STATE; }
    esp_err_t error = nvs_erase_key(nvs, a < b ? "snapshot_a" : "snapshot_b");
    return error == ESP_OK ? nvs_commit(nvs) : error;
}

static void iotmd_nvs_reclaim_obsolete_transactions(void) {
    // A bounded allowlist, not a partition-wide erase. Do not touch credentials,
    // network trials, paired-update state, or any unknown namespace/key.
    const char *names[] = {"v3qual", "v3qualhist", "v3qualcamp", "apiops"};
    for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
        nvs_handle_t nvs;
        // A read-only probe prevents creating namespaces on older devices.
        // Only reopen a namespace that is already present.
        if (nvs_open(names[index], NVS_READONLY, &nvs) != ESP_OK) { continue; }
        nvs_close(nvs);
        if (nvs_open(names[index], NVS_READWRITE, &nvs) != ESP_OK) { continue; }
        // Best effort: a corrupt unrelated namespace is left untouched, and
        // the writer still fails normally if capacity cannot be reclaimed.
        (void)iotmd_nvs_reclaim_snapshot(nvs);
        nvs_close(nvs);
    }
}

#endif
