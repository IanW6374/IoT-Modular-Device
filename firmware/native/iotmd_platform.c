// Reset-persistent platform facilities required by the IoT-MD boot supervisor.

#include <string.h>

#include "py/obj.h"
#include "py/runtime.h"
#include "esp_attr.h"
#include "esp_heap_caps.h"

#define IOTMD_BACKUP_MEMORY_BYTES (768)

// RTC_NOINIT memory survives software resets and watchdog resets. Power loss
// intentionally leaves its content undefined; the Python record CRC and magic
// reject stale or random bytes before they are used.
RTC_NOINIT_ATTR static uint8_t iotmd_backup_memory[IOTMD_BACKUP_MEMORY_BYTES];
RTC_NOINIT_ATTR static size_t iotmd_backup_memory_length;

static mp_obj_t iotmd_platform_backup_memory(size_t n_args,
    const mp_obj_t *args) {
    if (n_args == 0) {
        if (iotmd_backup_memory_length > IOTMD_BACKUP_MEMORY_BYTES) {
            return mp_const_empty_bytes;
        }
        return mp_obj_new_bytes(
            iotmd_backup_memory, iotmd_backup_memory_length
        );
    }

    mp_buffer_info_t input;
    mp_get_buffer_raise(args[0], &input, MP_BUFFER_READ);
    if (input.len > IOTMD_BACKUP_MEMORY_BYTES) {
        mp_raise_ValueError(MP_ERROR_TEXT("backup-memory record is too large"));
    }
    memset(iotmd_backup_memory, 0, sizeof(iotmd_backup_memory));
    if (input.len) {
        memcpy(iotmd_backup_memory, input.buf, input.len);
    }
    iotmd_backup_memory_length = input.len;
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    iotmd_platform_backup_memory_obj, 0, 1, iotmd_platform_backup_memory
);

static mp_obj_t iotmd_platform_transport_resources(void) {
    mp_obj_t result = mp_obj_new_dict(4);
    const uint32_t internal = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;
    const uint32_t dma = MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA | MALLOC_CAP_8BIT;
    mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_internal_free),
        mp_obj_new_int_from_uint(heap_caps_get_free_size(internal)));
    mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_internal_largest),
        mp_obj_new_int_from_uint(heap_caps_get_largest_free_block(internal)));
    mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_dma_free),
        mp_obj_new_int_from_uint(heap_caps_get_free_size(dma)));
    mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_dma_largest),
        mp_obj_new_int_from_uint(heap_caps_get_largest_free_block(dma)));
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_0(
    iotmd_platform_transport_resources_obj, iotmd_platform_transport_resources
);

static const mp_rom_map_elem_t iotmd_platform_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR__iotmd_platform) },
    { MP_ROM_QSTR(MP_QSTR_backup_memory),
      MP_ROM_PTR(&iotmd_platform_backup_memory_obj) },
    { MP_ROM_QSTR(MP_QSTR_transport_resources),
      MP_ROM_PTR(&iotmd_platform_transport_resources_obj) },
};
static MP_DEFINE_CONST_DICT(
    iotmd_platform_module_globals,
    iotmd_platform_module_globals_table
);

const mp_obj_module_t iotmd_platform_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&iotmd_platform_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR__iotmd_platform, iotmd_platform_user_cmodule);
