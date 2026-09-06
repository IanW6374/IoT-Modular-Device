"""Production driver inventory bridge for all supported IoT-MD v2 variants."""

from device_modules.driver_index import DRIVER_MODULES
from device_modules.resources import resources_for_device

from .drivers import SUPPORTED_DRIVER_TYPES


TYPE_TO_DRIVER = {}
for driver, variants in SUPPORTED_DRIVER_TYPES.items():
    for variant in variants:
        TYPE_TO_DRIVER[variant] = driver


def _variant(device):
    kind = device.get('type') or {}
    return str(kind.get('class', '')) + ':' + str(kind.get('subclass', ''))


def _signature(value):
    if value is None:
        return ''
    if isinstance(value, (list, tuple)):
        value = ','.join(str(item) for item in value)
    return str(value)[:64]


def _parameters(device, declaration):
    kind = declaration['kind']
    if kind == 'uart':
        section = device.get('rs485') or device.get('ems') or {}
        ports = section.get('ports') if isinstance(section, dict) else None
        if isinstance(ports, dict):
            match = next((item for item in ports.values()
                          if item.get('uart') == declaration['id']), {})
        else:
            match = section
        return {
            'tx': int(match.get('tx', -1)), 'rx': int(match.get('rx', -1)),
            'baudrate': int(match.get('baudrate', 9600)),
            'rx_buffer': int(match.get('rx_buffer', 512)),
        }
    if kind == 'spi':
        section = device.get('max31865') or {}
        return {
            'sck': int(section.get('sck', 12)),
            'mosi': int(section.get('mosi', 11)),
            'miso': int(section.get('miso', 13)),
            'dma_channel': int(section.get('dma_channel', 0)),
        }
    if kind == 'adc':
        section = device.get('ac_voltage') or {}
        return {
            'attenuation': int(section.get('attenuation', 11)),
            'bitwidth': int(section.get('bitwidth', 12)),
        }
    if kind == 'gpio':
        return {'mode': 0, 'pull': 0, 'level': 0, 'interrupt': 0}
    return {}


def translate_v2_modules(devices):
    """Translate validated v2 module declarations without constructing I/O."""
    result = []
    for index, device in enumerate(devices or ()):
        variant = _variant(device)
        if variant not in DRIVER_MODULES or variant not in TYPE_TO_DRIVER:
            raise ValueError('unsupported production driver variant: ' + variant)
        resources = []
        for item in resources_for_device(device):
            shared = bool(item.get('shared', False))
            resources.append({
                'kind': str(item['kind']),
                'identifier': str(item['kind']) + ':' + str(item['id']),
                'shared': shared,
                'signature': _signature(item.get('signature')) if shared else '',
                'parameters': _parameters(device, item),
            })
        if not resources:
            raise ValueError('driver has no declared physical resources: ' + variant)
        result.append({
            'id': str(device.get('uuid') or ('module-' + str(index + 1)))[:32],
            'driver': TYPE_TO_DRIVER[variant], 'enabled': True,
            'resources': resources,
            'settings': {'variant': variant},
        })
    return result


def validate_complete_driver_catalog():
    declared = set(DRIVER_MODULES)
    supported = set(TYPE_TO_DRIVER)
    if declared != supported:
        missing = sorted(declared ^ supported)
        raise RuntimeError('v3 driver catalog mismatch: ' + ', '.join(missing))
    return {'variants': len(declared), 'drivers': len(SUPPORTED_DRIVER_TYPES)}
