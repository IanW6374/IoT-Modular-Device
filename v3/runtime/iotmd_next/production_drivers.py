"""V3-owned translation of supported legacy module declarations.

The compatibility configuration schema is accepted at this migration edge,
but the native-v3 driver path deliberately has no imports from the v2 driver
implementation or its logical resource manager.
"""

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


def _gpio(declarations, value, role, shared=False):
    if isinstance(value, int) and not isinstance(value, bool):
        declarations.append({
            'kind': 'gpio', 'id': value, 'shared': bool(shared),
            'signature': role if shared else None, 'name': role,
        })


def _resources_for_device(device):
    """Translate the compatibility schema into v3 physical claims."""
    declarations = []
    for section_name in ('rs485', 'ems'):
        section = device.get(section_name)
        if not isinstance(section, dict):
            continue
        ports = section.get('ports')
        if isinstance(ports, dict):
            for port_name in sorted(ports):
                port = ports[port_name]
                if not isinstance(port, dict):
                    continue
                if port.get('uart') is not None:
                    declarations.append({
                        'kind': 'uart', 'id': port['uart'],
                        'name': section_name + '.' + str(port_name) + '.uart',
                    })
                for field in ('tx', 'rx', 'de'):
                    _gpio(declarations, port.get(field),
                          section_name + '.' + str(port_name) + '.' + field)
            continue
        if section.get('uart') is not None:
            declarations.append({
                'kind': 'uart', 'id': section['uart'],
                'name': section_name + '.uart',
            })
        for field in ('tx', 'rx', 'de'):
            _gpio(declarations, section.get(field), section_name + '.' + field)

    spi = device.get('max31865')
    if isinstance(spi, dict):
        bus = spi.get('spi', 0)
        declarations.append({
            'kind': 'spi', 'id': bus, 'shared': True,
            'signature': tuple(spi.get(name) for name in (
                'sck', 'mosi', 'miso', 'baudrate', 'polarity', 'phase',
                'bits', 'firstbit')),
            'name': 'max31865.spi',
        })
        for field in ('sck', 'mosi', 'miso'):
            _gpio(declarations, spi.get(field),
                  'spi.' + str(bus) + '.' + field, True)
        _gpio(declarations, spi.get('cs'), 'max31865.cs')

    voltage = device.get('ac_voltage')
    if isinstance(voltage, dict) and voltage.get('adc_pin') is not None:
        pin = voltage['adc_pin']
        declarations.append({'kind': 'adc', 'id': pin,
                             'name': 'ac_voltage.adc'})
        _gpio(declarations, pin, 'ac_voltage.adc.gpio')

    gpio = device.get('gpio')
    if isinstance(gpio, dict):
        for direction in ('input', 'output'):
            mapping = gpio.get(direction)
            if isinstance(mapping, dict):
                for pin in mapping.values():
                    _gpio(declarations, pin, 'gpio.' + direction)
    return declarations


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
        if variant not in TYPE_TO_DRIVER:
            raise ValueError('unsupported production driver variant: ' + variant)
        resources = []
        for item in _resources_for_device(device):
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
    declared = [
        variant for variants in SUPPORTED_DRIVER_TYPES.values()
        for variant in variants
    ]
    if len(declared) != len(set(declared)) or set(declared) != set(TYPE_TO_DRIVER):
        raise RuntimeError('v3 driver catalog contains duplicate variants')
    return {'variants': len(declared), 'drivers': len(SUPPORTED_DRIVER_TYPES)}
