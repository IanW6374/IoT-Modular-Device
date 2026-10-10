"""Execute native retention and the actual commit body against bounded NVS.

This is fault-injection coverage, not a claim of physical NVS power-cut testing.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'firmware/native'

NVS_STUB = r'''
#ifndef TEST_NVS_H
#define TEST_NVS_H
#include <stddef.h>
typedef int esp_err_t;
typedef int nvs_handle_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_NO_MEM 0x101
#define ESP_ERR_INVALID_STATE 0x103
#define ESP_ERR_NVS_NOT_FOUND 0x1102
#define ESP_ERR_NVS_NOT_ENOUGH_SPACE 0x1105
#define NVS_READONLY 0
#define NVS_READWRITE 1
int nvs_get_blob(int, const char *, void *, size_t *);
int nvs_set_blob(int, const char *, const void *, size_t);
int nvs_erase_key(int, const char *);
int nvs_commit(int);
int nvs_open(const char *, int, int *);
void nvs_close(int);
#endif
'''

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <setjmp.h>
#include <stdio.h>
#include "iotmd_nvs_retention.h"

static const char *names[] = {
    "v3qual", "v3qualhist", "v3qualcamp", "apiops",
    "iotmd_config", "v3paired", "unrelated"
};
typedef struct { bool present; size_t size; unsigned char data[8192]; } slot;
static slot slots[7][2];
static bool existing[7];
static int open_count, creates, erases, commits, writes, failure, fault_step;
static size_t capacity = 100000;
static jmp_buf interrupted;

static int key_index(const char *key) {
    if (!strcmp(key,"snapshot_a") || !strcmp(key,"cfg0")) return 0;
    if (!strcmp(key,"snapshot_b") || !strcmp(key,"cfg1")) return 1;
    assert(false); return -1;
}
static void transition(void) {
    if (fault_step > 0 && --fault_step == 0) longjmp(interrupted, 1);
}
static size_t used(void) {
    size_t total=0;
    for(int n=0;n<7;n++)for(int k=0;k<2;k++)if(slots[n][k].present)total+=slots[n][k].size;
    return total;
}
int nvs_open(const char *name, int mode, int *handle) {
    for(int n=0;n<7;n++)if(!strcmp(name,names[n])){
        if(!existing[n] && mode==NVS_READONLY)return ESP_ERR_NVS_NOT_FOUND;
        if(!existing[n]){existing[n]=true;creates++;}
        *handle=n;open_count++;return ESP_OK;
    }
    assert(false);return ESP_FAIL;
}
void nvs_close(int handle) { (void)handle;assert(open_count>0);open_count--; }
int nvs_get_blob(int n,const char *key,void *buffer,size_t *length) {
    slot *s=&slots[n][key_index(key)];
    if(!s->present)return ESP_ERR_NVS_NOT_FOUND;
    if(failure==1)return ESP_FAIL;
    if(buffer){assert(*length>=s->size);memcpy(buffer,s->data,s->size);}
    *length=s->size;return ESP_OK;
}
int nvs_erase_key(int n,const char *key) {
    // Any accidental configuration/paired/unknown erase fails the test.
    assert(n<4);
    if(failure==2 || (failure==6 && writes))return ESP_FAIL;
    slot *s=&slots[n][key_index(key)];
    if(!s->present)return ESP_ERR_NVS_NOT_FOUND;
    s->present=false;erases++;transition();return ESP_OK;
}
int nvs_commit(int n) {
    (void)n;commits++;
    if(failure==3 || (failure==7 && writes && erases))return ESP_FAIL;
    transition();return ESP_OK;
}
int nvs_set_blob(int n,const char *key,const void *buffer,size_t length) {
    assert(n<4);slot *s=&slots[n][key_index(key)];
    if(failure==4)return ESP_ERR_NVS_NOT_ENOUGH_SPACE;
    if(used()-(s->present?s->size:0)+length>capacity)return ESP_ERR_NVS_NOT_ENOUGH_SPACE;
    assert(length<=sizeof(s->data));
    memcpy(s->data,buffer,length);s->size=length;s->present=true;writes++;
    if(failure==5)s->data[length-1]^=1; // Verify before discarding predecessor.
    transition();return ESP_OK;
}
static void u32_write(unsigned char *b,uint32_t v) {
    b[0]=v;b[1]=v>>8;b[2]=v>>16;b[3]=v>>24;
}
static void seed(int n,int k,uint32_t generation,size_t size) {
    assert(size>=16 && size<=4112);slot *s=&slots[n][k];
    existing[n]=true;s->present=true;s->size=size;
    memset(s->data,'x',size);memcpy(s->data,"I3TX",4);
    u32_write(s->data+4,generation);u32_write(s->data+8,size-16);
    u32_write(s->data+12,iotmd_nvs_crc32(s->data+16,size-16));
}
static void reset(void) {
    memset(slots,0,sizeof(slots));memset(existing,0,sizeof(existing));
    open_count=creates=erases=commits=writes=failure=fault_step=0;capacity=100000;
}
static uint32_t latest(int n) {
    uint32_t a=0,b=0;
    int ea=iotmd_nvs_snapshot_generation(n,"snapshot_a",&a);
    int eb=iotmd_nvs_snapshot_generation(n,"snapshot_b",&b);
    if (ea != ESP_OK) { a = 0; }
    if (eb != ESP_OK) { b = 0; }
    return a > b ? a : b;
}

// Minimal MicroPython ABI stubs; compile the unmodified native commit body.
typedef uintptr_t mp_obj_t;
typedef intptr_t mp_int_t;
typedef struct { const void *buf; size_t len; } mp_buffer_info_t;
typedef struct { int nvs; const char *namespace_name; } iotmd_v3_storage_handle_t;
static iotmd_v3_storage_handle_t target = {3,"apiops"};
#define mp_const_none 0
#define MP_BUFFER_READ 0
#define MP_EIO 5
#define MP_EAGAIN 11
#define MP_ERROR_TEXT(x) x
#define IOTMD_V3_STORAGE_MAX_PAYLOAD 4096
#define IOTMD_V3_STORAGE_HEADER_BYTES 16
#define m_new(type,length) ((type *)malloc((length)*sizeof(type)))
#define m_del(type,buffer,length) free(buffer)
static int last_error, mp_type_RuntimeError;
static void mp_raise_OSError(int error) { last_error=error;longjmp(interrupted,2); }
static void mp_raise_ValueError(const char *message) { (void)message;mp_raise_OSError(22); }
static void mp_raise_msg(int *type,const char *message) { (void)type;(void)message;mp_raise_OSError(22); }
static mp_int_t mp_obj_get_int(mp_obj_t value) { return value; }
static mp_obj_t mp_obj_new_int_from_uint(uint32_t value) { return value; }
static void mp_get_buffer_raise(mp_obj_t value,mp_buffer_info_t *out,int flags) {
    (void)flags;*out=*(mp_buffer_info_t *)value;
}
static iotmd_v3_storage_handle_t *iotmd_v3_storage_handle(mp_obj_t value) {
    assert(value==1);return &target;
}
static void iotmd_v3_validate_apiops_storage(iotmd_v3_storage_handle_t *handle) {
    for(int k=0;k<2;k++){
        uint32_t generation;
        int error=iotmd_nvs_snapshot_generation(handle->nvs,k?"snapshot_b":"snapshot_a",&generation);
        if(error!=ESP_OK && error!=ESP_ERR_NVS_NOT_FOUND)mp_raise_OSError(MP_EIO);
    }
}
static bool iotmd_v3_storage_latest(int n,uint32_t *generation,mp_obj_t *payload) {
    *generation=latest(n);*payload=0;return *generation!=0;
}
static void iotmd_v3_u32_write(uint8_t *out,uint32_t value) { u32_write(out,value); }
static uint32_t iotmd_v3_crc32(const uint8_t *value,size_t size) {return iotmd_nvs_crc32(value,size);}
__ACTUAL_COMMIT_BODY__

static mp_obj_t write_generation(uint32_t expected,size_t size) {
    static unsigned char payload[4096];memset(payload,'y',size>sizeof(payload)?sizeof(payload):size);
    mp_buffer_info_t source={payload,size};
    mp_obj_t args[]={1,expected,(mp_obj_t)&source};
    return iotmd_platform_v3_storage_commit(3,args);
}
static void pressure_seed(void) {
    reset();
    for(int n=0;n<4;n++){seed(n,0,4,n==1?2000:1000);seed(n,1,5,n==1?2000:1000);}
    for(int n=4;n<7;n++){seed(n,0,4,1000);seed(n,1,5,1000);}
    capacity=12500;assert(used()==16000);
}
int main(void) {
    reset();iotmd_nvs_reclaim_obsolete_transactions();
    assert(!creates && !erases && !open_count);
    seed(3,0,6,200);seed(3,1,5,200);
    assert(iotmd_nvs_reclaim_snapshot(3)==ESP_OK);
    assert(slots[3][0].present && !slots[3][1].present && latest(3)==6);
    assert(iotmd_nvs_reclaim_snapshot(3)==ESP_OK && erases==1);

    // Invalid CRC/header/parity or an unreadable snapshot prevents reclamation.
    for(int mode=0;mode<6;mode++){
        reset();seed(3,0,4,200);seed(3,1,5,200);
        if(mode==0)slots[3][1].data[199]^=1;
        if(mode==1)slots[3][1].data[0]='?';
        if(mode==2)u32_write(slots[3][1].data+8,0);
        if(mode==3)u32_write(slots[3][1].data+4,0);
        if(mode==4)u32_write(slots[3][1].data+4,4);
        if(mode==5)failure=1;
        assert(iotmd_nvs_reclaim_snapshot(3)!=ESP_OK);
        assert(!erases && slots[3][0].present && slots[3][1].present);
    }
    // Only allowlisted, older copies are freed. Current watermarks stay exact.
    pressure_seed();iotmd_nvs_reclaim_obsolete_transactions();
    assert(!open_count && !creates && erases==4 && used()==11000);
    for(int n=0;n<7;n++)assert(latest(n)==5);
    for(int n=4;n<7;n++)assert(slots[n][0].present && slots[n][1].present);
    assert(write_generation(5,1024)==6);
    assert(latest(3)==6 && slots[3][0].present && !slots[3][1].present);

    // True capacity exhaustion remains an error, never permission to delete
    // the sole/latest generation or API client ledger to make a write fit.
    reset();seed(3,1,5,1000);capacity=1100;
    if(!setjmp(interrupted)){write_generation(5,1000);assert(false);}
    assert(last_error==ESP_ERR_NVS_NOT_ENOUGH_SPACE && latest(3)==5);
    assert(!erases && !writes && !creates);

    // Actual commit still checks CAS, payload bounds and corruption first.
    reset();seed(3,1,5,1000);last_error=0;
    if(!setjmp(interrupted)){write_generation(4,10);assert(false);}
    assert(last_error==MP_EAGAIN && !erases && !writes);
    if(!setjmp(interrupted)){write_generation(5,4097);assert(false);}
    assert(last_error==22 && !erases && !writes);
    slots[3][1].data[999]^=1;
    if(!setjmp(interrupted)){write_generation(5,10);assert(false);}
    assert(last_error==MP_EIO && !erases && !writes);

    // Failure to allocate/commit/read-back cannot delete the prior good state.
    for(int mode=2;mode<=5;mode++){
        reset();seed(3,1,5,1000);failure=mode;
        if(!setjmp(interrupted)){write_generation(5,1000);assert(false);}
        assert(slots[3][1].present);failure=0;
        assert(latest(3)>=5);
    }
    // Interrupt after every mutating boundary, including cross-namespace
    // reclamation and the new write. Never fall below a committed watermark.
    for(int step=1;step<=13;step++){
        pressure_seed();fault_step=step;
        if(!setjmp(interrupted))assert(write_generation(5,1024)==6);
        fault_step=0;
        assert(latest(3)>=5);
        for(int n=0;n<7;n++)assert(latest(n)>=5);
        for(int n=4;n<7;n++)assert(slots[n][0].present && slots[n][1].present);
    }
    // Corrupt unrelated namespaces are retained; other verified old copies
    // may be reclaimed, but we never silently recover an old API watermark.
    pressure_seed();slots[1][1].data[1999]^=1;
    iotmd_nvs_reclaim_obsolete_transactions();
    assert(slots[1][0].present && slots[1][1].present);
    assert(latest(3)==5 && !slots[3][0].present);
    // Cleanup errors after verification cannot negate a durable acknowledgement.
    // Retention may be attempted again without executing another device action.
    for(int mode=6;mode<=7;mode++){
        reset();seed(3,1,5,200);failure=mode;
        assert(write_generation(5,200)==6);
        assert(latest(3)==6 && slots[3][0].present);
        if(mode==6)assert(slots[3][1].present);
    }
    puts("NVS retention and native commit fault checks passed");
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class NativeNvsRetentionTests(unittest.TestCase):
    def test_retention_capacity_and_interrupted_native_commit(self):
        source = (NATIVE / 'iotmd_platform_v3.c').read_text()
        start = source.index('static mp_obj_t iotmd_platform_v3_storage_commit(')
        end = source.index('static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(', start)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nvs.h').write_text(NVS_STUB)
            harness = root / 'retention.c'
            harness.write_text(HARNESS.replace('__ACTUAL_COMMIT_BODY__', source[start:end]))
            binary = root / 'retention'
            compiled = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                                       '-Wno-unused-parameter', '-I', str(root), '-I', str(NATIVE),
                                       str(harness), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('native commit fault checks passed', result.stdout)
