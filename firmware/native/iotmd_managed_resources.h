// ABI 7: core-owned MicroPython peripheral objects. Never expose a raw object
// to application drivers: every call revalidates its generation-safe lease.
#include "py/objtuple.h"
#include "py/nlr.h"

static int iotmd_managed_pin(int number) {
    // ESP32-S3 N8R8 flash/PSRAM, USB, boot and UART console remain core-owned.
    if (!GPIO_IS_VALID_GPIO(number) || number == 0 || number == 19 || number == 20 ||
            (number >= 26 && number <= 37) || number == 43 || number == 44) {
        mp_raise_ValueError(MP_ERROR_TEXT("pin is reserved by the secure core"));
    }
    return number;
}

static mp_obj_t iotmd_managed_machine(void) {
    return mp_import_name(MP_QSTR_machine, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
}

static void iotmd_v3_managed_deinit(iotmd_v3_resource_claim_t *claim) {
    size_t index = claim - iotmd_v3_resource_claims;
    mp_obj_t object = MP_STATE_PORT(iotmd_resource_objects)[index];
    if (claim->constructed && !iotmd_v3_resource_peer_constructed(claim)) {
        mp_obj_t method[2];
        if (strcmp(claim->kind, "uart") == 0 || strcmp(claim->kind, "gpio") == 0) {
            mp_obj_t irq_args[] = {object, MP_OBJ_NULL, MP_OBJ_NEW_QSTR(MP_QSTR_handler), mp_const_none};
            mp_load_method(object, MP_QSTR_irq, irq_args);
            mp_call_method_n_kw(0, 1, irq_args);
        }
        mp_load_method_maybe(object, MP_QSTR_deinit, method);
        if (method[0] != MP_OBJ_NULL) {
            mp_call_method_n_kw(0, 0, method);
        } else if (strcmp(claim->kind, "gpio") == 0) {
            gpio_reset_pin(iotmd_managed_pin(iotmd_v3_resource_number(
                claim->identifier, "gpio", 0, GPIO_NUM_MAX - 1)));
        }
    }
    MP_STATE_PORT(iotmd_resource_objects)[index] = MP_OBJ_NULL;
    MP_STATE_PORT(iotmd_resource_parameters)[index] = MP_OBJ_NULL;
    claim->constructed = false;
    claim->managed_object = false;
}

static mp_obj_t iotmd_platform_v3_resource_object(mp_obj_t handle_in, mp_obj_t parameters) {
    size_t index;
    iotmd_v3_resource_claim_t *claim = iotmd_v3_resource_handle(handle_in, &index);
    if (!mp_obj_is_type(parameters, &mp_type_dict)) {
        mp_raise_ValueError(MP_ERROR_TEXT("peripheral configuration must be a dict"));
    }
    if (claim->constructed) {
        mp_raise_OSError(MP_EBUSY);
    }
    qstr type = MP_QSTR_Pin;
    int maximum = GPIO_NUM_MAX - 1;
    int minimum = 0;
    const qstr gpio_keys[] = {MP_QSTR_mode, MP_QSTR_pull, MP_QSTR_value};
    const qstr uart_keys[] = {MP_QSTR_tx, MP_QSTR_rx, MP_QSTR_baudrate, MP_QSTR_bits,
        MP_QSTR_parity, MP_QSTR_stop, MP_QSTR_timeout, MP_QSTR_timeout_char, MP_QSTR_rxbuf};
    const qstr spi_keys[] = {MP_QSTR_sck, MP_QSTR_mosi, MP_QSTR_miso, MP_QSTR_baudrate,
        MP_QSTR_polarity, MP_QSTR_phase, MP_QSTR_bits, MP_QSTR_firstbit};
    const qstr adc_keys[] = {MP_QSTR_atten};
    const qstr pwm_keys[] = {MP_QSTR_freq, MP_QSTR_duty_u16};
    const qstr i2c_keys[] = {MP_QSTR_sda, MP_QSTR_scl, MP_QSTR_freq, MP_QSTR_timeout};
    const qstr *allowed = gpio_keys;
    size_t allowed_count = MP_ARRAY_SIZE(gpio_keys);
    if (strcmp(claim->kind, "uart") == 0) {
        type = MP_QSTR_UART; minimum = 1; maximum = UART_NUM_MAX - 1;
        allowed = uart_keys; allowed_count = MP_ARRAY_SIZE(uart_keys);
    } else if (strcmp(claim->kind, "spi") == 0) {
        type = MP_QSTR_SPI; minimum = 1; maximum = 2;
        allowed = spi_keys; allowed_count = MP_ARRAY_SIZE(spi_keys);
    } else if (strcmp(claim->kind, "adc") == 0) {
        type = MP_QSTR_ADC; allowed = adc_keys; allowed_count = MP_ARRAY_SIZE(adc_keys);
    } else if (strcmp(claim->kind, "pwm") == 0) {
        type = MP_QSTR_PWM; allowed = pwm_keys; allowed_count = MP_ARRAY_SIZE(pwm_keys);
    } else if (strcmp(claim->kind, "i2c") == 0) {
        type = MP_QSTR_I2C; maximum = 1;
        allowed = i2c_keys; allowed_count = MP_ARRAY_SIZE(i2c_keys);
    }
    int number = iotmd_v3_resource_number(claim->identifier, claim->kind, minimum, maximum);
    if (type == MP_QSTR_Pin || type == MP_QSTR_ADC || type == MP_QSTR_PWM) {
        iotmd_managed_pin(number);
        if (type != MP_QSTR_Pin) {
            char identifier[16];
            snprintf(identifier, sizeof(identifier), "gpio:%d", number);
            bool owned = false;
            for (size_t p = 0; p < IOTMD_V3_RESOURCE_CLAIMS; ++p) {
                iotmd_v3_resource_claim_t *other = &iotmd_v3_resource_claims[p];
                owned |= other->used && strcmp(other->kind, "gpio") == 0 &&
                    strcmp(other->owner, claim->owner) == 0 && strcmp(other->identifier, identifier) == 0;
            }
            if (!owned) { mp_raise_OSError(MP_EPERM); }
        }
    }
    mp_map_t *map = mp_obj_dict_get_map(parameters);
    if (map->used > allowed_count) {
        mp_raise_ValueError(MP_ERROR_TEXT("too many peripheral parameters"));
    }
    mp_obj_t args[25];
    args[0] = mp_obj_new_int(number);
    size_t count = 0;
    for (size_t item = 0; item < map->alloc; ++item) {
        if (!mp_map_slot_is_filled(map, item)) { continue; }
        qstr key = mp_obj_str_get_qstr(map->table[item].key);
        bool valid = false;
        for (size_t k = 0; k < allowed_count; ++k) { valid |= key == allowed[k]; }
        if (!valid || !(mp_obj_is_int(map->table[item].value) || map->table[item].value == mp_const_none)) {
            mp_raise_ValueError(MP_ERROR_TEXT("invalid peripheral parameter"));
        }
        if ((key == MP_QSTR_rxbuf || key == MP_QSTR_timeout || key == MP_QSTR_timeout_char) &&
                (mp_obj_get_int(map->table[item].value) < 0 || mp_obj_get_int(map->table[item].value) > 4096)) {
            mp_raise_ValueError(MP_ERROR_TEXT("UART buffer or timeout exceeds resource limit"));
        }
        if (key == MP_QSTR_tx || key == MP_QSTR_rx || key == MP_QSTR_sck ||
                key == MP_QSTR_mosi || key == MP_QSTR_miso || key == MP_QSTR_sda || key == MP_QSTR_scl) {
            if (map->table[item].value != mp_const_none) {
                int pin = iotmd_managed_pin(mp_obj_get_int(map->table[item].value));
                char identifier[16];
                snprintf(identifier, sizeof(identifier), "gpio:%d", pin);
                bool owned = false;
                for (size_t p = 0; p < IOTMD_V3_RESOURCE_CLAIMS; ++p) {
                    iotmd_v3_resource_claim_t *other = &iotmd_v3_resource_claims[p];
                    owned |= other->used && strcmp(other->kind, "gpio") == 0 &&
                        strcmp(other->owner, claim->owner) == 0 && strcmp(other->identifier, identifier) == 0;
                }
                if (!owned) { mp_raise_OSError(MP_EPERM); }
            }
        }
        args[1 + count * 2] = MP_OBJ_NEW_QSTR(key);
        args[2 + count * 2] = map->table[item].value;
        ++count;
    }
    const iotmd_v3_resource_claim_t *peer = iotmd_v3_resource_constructed_peer(claim);
    if (peer != NULL) {
        if (!peer->managed_object) { mp_raise_OSError(MP_EBUSY); }
        if (!mp_obj_equal(parameters, MP_STATE_PORT(iotmd_resource_parameters)[peer - iotmd_v3_resource_claims])) {
            mp_raise_ValueError(MP_ERROR_TEXT("shared peripheral parameters differ"));
        }
        MP_STATE_PORT(iotmd_resource_objects)[index] =
            MP_STATE_PORT(iotmd_resource_objects)[peer - iotmd_v3_resource_claims];
    } else {
        MP_STATE_PORT(iotmd_resource_objects)[index] = mp_call_function_n_kw(
            mp_load_attr(iotmd_managed_machine(), type), 1, count, args);
    }
    claim->managed_object = true;
    claim->constructed = true;
    mp_obj_t copy = mp_obj_new_dict(map->used);
    for (size_t i = 0; i < map->alloc; ++i) {
        if (mp_map_slot_is_filled(map, i)) {
            mp_obj_dict_store(copy, map->table[i].key, map->table[i].value);
        }
    }
    MP_STATE_PORT(iotmd_resource_parameters)[index] = copy;
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_2(iotmd_platform_v3_resource_object_obj, iotmd_platform_v3_resource_object);

static mp_obj_t iotmd_platform_v3_resource_call(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    size_t index;
    iotmd_v3_resource_claim_t *claim = iotmd_v3_resource_handle(args[0], &index);
    if (!claim->constructed || !claim->managed_object) { mp_raise_OSError(MP_EPERM); }
    qstr name = mp_obj_str_get_qstr(args[1]);
    // Configuration is immutable except GPIO values and PWM frequency/duty.
    const char *methods = strcmp(claim->kind, "gpio") == 0 ? "|value|on|off|irq|" :
        strcmp(claim->kind, "pwm") == 0 ? "|freq|duty_u16|duty|" :
        strcmp(claim->kind, "adc") == 0 ? "|read|read_u16|read_uv|" :
        strcmp(claim->kind, "uart") == 0 ? "|read|readinto|write|any|flush|irq|" :
        strcmp(claim->kind, "spi") == 0 ? "|read|readinto|write|write_readinto|" :
        "|scan|readfrom|readfrom_into|writeto|readfrom_mem|readfrom_mem_into|writeto_mem|";
    char needle[40];
    snprintf(needle, sizeof(needle), "|%s|", qstr_str(name));
    if (strlen(qstr_str(name)) > 32 || strstr(methods, needle) == NULL) {
        mp_raise_ValueError(MP_ERROR_TEXT("peripheral method is not permitted"));
    }
    size_t positional;
    mp_obj_t *values;
    mp_obj_get_array(args[2], &positional, &values);
    if (!mp_obj_is_type(args[3], &mp_type_dict) || positional > 4) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid peripheral call"));
    }
    mp_map_t *keywords = mp_obj_dict_get_map(args[3]);
    if (keywords->used > 3) { mp_raise_ValueError(MP_ERROR_TEXT("too many peripheral arguments")); }
    mp_obj_t call[12];
    mp_load_method(MP_STATE_PORT(iotmd_resource_objects)[index], name, call);
    for (size_t i = 0; i < positional; ++i) {
        bool read_count = (name == MP_QSTR_read && i == 0) ||
            (name == MP_QSTR_readinto && i == 1) ||
            (name == MP_QSTR_readfrom && i == 1) ||
            (name == MP_QSTR_readfrom_mem && i == 2);
        if (read_count && mp_obj_is_int(values[i]) &&
                (mp_obj_get_int(values[i]) < 0 || mp_obj_get_int(values[i]) > 4096)) {
            mp_raise_ValueError(MP_ERROR_TEXT("peripheral transfer is too large"));
        }
        mp_buffer_info_t buffer;
        if (mp_get_buffer(values[i], &buffer, MP_BUFFER_READ) && buffer.len > 4096) {
            mp_raise_ValueError(MP_ERROR_TEXT("peripheral transfer is too large"));
        }
        call[2 + i] = values[i];
    }
    size_t count = 0;
    for (size_t i = 0; i < keywords->alloc; ++i) {
        if (!mp_map_slot_is_filled(keywords, i)) { continue; }
        qstr key = mp_obj_str_get_qstr(keywords->table[i].key);
        mp_obj_t value = keywords->table[i].value;
        if (key == MP_QSTR_nbytes && mp_obj_is_int(value) &&
                (mp_obj_get_int(value) < 0 || mp_obj_get_int(value) > 4096)) {
            mp_raise_ValueError(MP_ERROR_TEXT("peripheral transfer is too large"));
        }
        mp_buffer_info_t buffer;
        if (mp_get_buffer(value, &buffer, MP_BUFFER_READ) && buffer.len > 4096) {
            mp_raise_ValueError(MP_ERROR_TEXT("peripheral transfer is too large"));
        }
        if (name == MP_QSTR_irq && key == MP_QSTR_hard &&
                mp_obj_is_true(keywords->table[i].value)) {
            mp_raise_ValueError(MP_ERROR_TEXT("managed UART callbacks must use soft interrupts"));
        }
        call[2 + positional + count * 2] = keywords->table[i].key;
        call[3 + positional + count * 2] = keywords->table[i].value;
        ++count;
    }
    return mp_call_method_n_kw(positional, count, call);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(iotmd_platform_v3_resource_call_obj, 4, 4, iotmd_platform_v3_resource_call);

static mp_obj_t iotmd_platform_v3_resource_sensor(size_t n_args, const mp_obj_t *args) {
    size_t index;
    iotmd_v3_resource_claim_t *claim = iotmd_v3_resource_handle(args[0], &index);
    if (!claim->constructed || !claim->managed_object || strcmp(claim->kind, "gpio") != 0) {
        mp_raise_OSError(MP_EPERM);
    }
    qstr name = mp_obj_str_get_qstr(args[1]);
    mp_obj_t pin = MP_STATE_PORT(iotmd_resource_objects)[index];
    if (name == MP_QSTR_dht11 && n_args == 2) {
        mp_obj_t dht = mp_import_name(MP_QSTR_dht, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_t sensor = mp_call_function_1(mp_load_attr(dht, MP_QSTR_DHT11), pin);
        mp_obj_t method[2];
        mp_load_method(sensor, MP_QSTR_measure, method); mp_call_method_n_kw(0, 0, method);
        mp_load_method(sensor, MP_QSTR_temperature, method);
        mp_obj_t result[2] = {mp_call_method_n_kw(0, 0, method), mp_const_none};
        mp_load_method(sensor, MP_QSTR_humidity, method); result[1] = mp_call_method_n_kw(0, 0, method);
        return mp_obj_new_tuple(2, result);
    }
    if (name == MP_QSTR_pulse && n_args == 4) {
        mp_int_t timeout = mp_obj_get_int(args[3]);
        if (timeout < 1 || timeout > 100000) { mp_raise_ValueError(MP_ERROR_TEXT("pulse timeout is out of range")); }
        mp_obj_t values[] = {pin, args[2], args[3]};
        return mp_call_function_n_kw(mp_load_attr(iotmd_managed_machine(), MP_QSTR_time_pulse_us), 3, 0, values);
    }
    mp_raise_ValueError(MP_ERROR_TEXT("unsupported native sensor operation"));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(iotmd_platform_v3_resource_sensor_obj, 2, 4, iotmd_platform_v3_resource_sensor);
