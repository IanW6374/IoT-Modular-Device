"""Preflight hardware-resource allocation for configured device modules."""


class ResourceConflict(ValueError):
    pass


class ResourceManager:
    """Reserve exclusive resources and consistently configured shared buses."""

    def __init__(self, providers=None, protected_pins=None):
        self._resources = {}
        self._logical = {}
        self._providers = dict(providers or {})
        self._instances = {}
        self.native = None
        for pin in protected_pins or ():
            self.reserve('gpio', pin, 'core')

    def enable_native(self, provider=None):
        from .native_resources import NativeBackend
        self.native = NativeBackend(self, provider)

    def release_owner(self, owner):
        if self.native:
            self.native.release_owner(str(owner))
        for key in tuple(self._resources):
            resource = self._resources[key]
            if str(owner) in resource['owners']:
                resource['owners'].remove(str(owner))
            if not resource['owners']:
                self._instances.pop(key, None)
                del self._resources[key]
                for name in tuple(self._logical):
                    if self._logical[name] == key:
                        del self._logical[name]

    def reserve(self, kind, identifier, owner, shared=False, signature=None,
                logical_name=None):
        key = str(kind) + ':' + str(identifier)
        owner = str(owner)
        current = self._resources.get(key)
        if current is None:
            self._resources[key] = {
                'kind': str(kind), 'id': str(identifier),
                'owners': [owner], 'shared': bool(shared),
                'signature': signature,
                'logical_names': [],
            }
            current = self._resources[key]
        elif not current['shared'] or not shared:
            raise ResourceConflict(
                key + ' is owned by ' + ', '.join(current['owners']) +
                '; requested by ' + owner
            )
        elif current.get('signature') != signature:
            raise ResourceConflict(
                key + ' has incompatible shared-bus configuration for ' + owner
            )
        elif owner not in current['owners']:
            current['owners'].append(owner)
        if logical_name:
            logical_name = str(logical_name)
            existing = self._logical.get(logical_name)
            if existing is not None and existing != key:
                raise ResourceConflict(
                    'logical resource ' + logical_name + ' already maps to ' + existing
                )
            self._logical[logical_name] = key
            if logical_name not in current['logical_names']:
                current['logical_names'].append(logical_name)
        return key

    def reserve_device(self, device):
        if not isinstance(device, dict):
            raise ValueError('device resource declaration must be an object')
        owner = str(device.get('uuid') or device.get('name') or 'unknown')
        declarations = resources_for_device(device)
        for declaration in declarations:
            self.reserve(
                declaration['kind'], declaration['id'], owner,
                declaration.get('shared', False), declaration.get('signature'),
                owner + '.' + declaration.get(
                    'name', declaration['kind'] + '.' + str(declaration['id'])
                )
            )
        return declarations

    def register_provider(self, kind, provider):
        if not callable(provider):
            raise ValueError('resource provider must be callable')
        self._providers[str(kind)] = provider

    def scope(self, owner):
        return ResourceScope(self, owner)

    def acquire(self, logical_name, owner, factory=None):
        key = self._logical.get(str(logical_name), str(logical_name))
        resource = self._resources.get(key)
        if resource is None:
            raise KeyError('unknown hardware resource ' + str(logical_name))
        if str(owner) not in resource['owners']:
            raise PermissionError(
                str(owner) + ' does not own hardware resource ' + str(logical_name)
            )
        if key not in self._instances:
            provider = factory or self._providers.get(resource['kind'])
            if provider is None:
                raise RuntimeError(
                    'no provider registered for hardware resource ' + resource['kind']
                )
            self._instances[key] = provider(dict(resource))
        return self._instances[key]

    def bindings_for(self, owner):
        owner = str(owner)
        return {
            name: key for name, key in self._logical.items()
            if owner in self._resources[key]['owners']
        }

    def snapshot(self):
        return [
            {
                'kind': value['kind'], 'id': value['id'],
                'owners': list(value['owners']), 'shared': value['shared'],
                'logical_names': list(value.get('logical_names', ())),
            }
            for _, value in sorted(self._resources.items())
        ]


class ResourceScope:
    """Owner-bound injection interface passed to resource-aware drivers."""

    def __init__(self, manager, owner):
        self.manager = manager
        self.owner = str(owner)

    def acquire(self, logical_name, factory=None):
        return self.manager.acquire(logical_name, self.owner, factory)

    def bindings(self):
        return self.manager.bindings_for(self.owner)

    def construct(self, kind, identifier, **parameters):
        if self.manager.native is None:
            raise RuntimeError('native driver resource backend is unavailable')
        return self.manager.native.construct(self.owner, kind, identifier, parameters)

    def pin(self, identifier, mode=0, pull=None, value=None):
        parameters = {'mode': mode, 'pull': pull}
        if value is not None:
            parameters['value'] = value
        return self.construct('gpio', identifier, **parameters)


def _gpio(declarations, value, role, shared=False):
    if isinstance(value, int) and not isinstance(value, bool):
        declarations.append({
            'kind': 'gpio', 'id': value, 'shared': bool(shared),
            'signature': role if shared else None,
            'name': role,
        })


def resources_for_device(device):
    """Return deterministic resources from the installed module configuration."""
    declarations = []
    device = dict(device)
    subtype = (device.get('type') or {}).get('subclass')
    if subtype in ('WHES', 'RS485-Modbus'):
        cfg = dict(device.get('rs485') or {})
        if cfg.get('ports'):
            if len(cfg['ports']) != 1:
                raise ValueError('single-port RS485 requires exactly one configured port')
            cfg['ports'] = {name: dict({'uart': 1, 'tx': 17, 'rx': 18}, **port)
                for name, port in cfg['ports'].items()}
        else:
            cfg = dict({'uart': 1, 'tx': 17, 'rx': 18}, **cfg)
        device['rs485'] = cfg
    elif subtype == 'RS485-Modbus-Multiport' and not (device.get('rs485') or {}).get('ports'):
        device['rs485'] = {'ports': {'ch0': {
            'uart': device.get('uart', 1), 'tx': device.get('tx', 8), 'rx': device.get('rx', 9)}}}
    elif subtype == 'RS485-Modbus-Multiport':
        cfg = dict(device.get('rs485') or {})
        cfg['ports'] = {name: dict({'uart': 1}, **port) for name, port in cfg['ports'].items()}
        if any(port.get('tx') is None or port.get('rx') is None for port in cfg['ports'].values()):
            raise ValueError('multiport RS485 requires explicit TX and RX pins for each port')
        device['rs485'] = cfg
    elif subtype == 'EMS-Boiler':
        device['ems'] = dict({'uart': 1, 'tx': 17, 'rx': 18}, **(device.get('ems') or {}))
    elif subtype == 'MAX31865-PT1000':
        device['max31865'] = dict({'spi': 1, 'sck': 2, 'mosi': 3, 'miso': 4,
            'cs': 5, 'baudrate': 1000000, 'polarity': 0, 'phase': 1,
            'bits': 8, 'firstbit': 0}, **(device.get('max31865') or {}))
    elif subtype == 'Grove-AC-Voltage':
        device['ac_voltage'] = dict({'adc_pin': device.get('adc_pin', 1)}, **(device.get('ac_voltage') or {}))

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
                uart = port.get('uart')
                if uart is not None:
                    declarations.append({
                        'kind': 'uart', 'id': uart,
                        'name': section_name + '.' + str(port_name) + '.uart',
                    })
                for field in ('tx', 'rx', 'de'):
                    _gpio(
                        declarations, port.get(field),
                        section_name + '.' + str(port_name) + '.' + field
                    )
            continue
        uart = section.get('uart')
        if uart is not None:
            declarations.append({
                'kind': 'uart', 'id': uart,
                'name': section_name + '.uart',
            })
        for field in ('tx', 'rx', 'de'):
            _gpio(declarations, section.get(field), section_name + '.' + field)

    spi = device.get('max31865')
    if isinstance(spi, dict):
        bus = spi.get('spi', 0)
        signature = tuple(spi.get(name) for name in (
            'sck', 'mosi', 'miso', 'baudrate', 'polarity', 'phase', 'bits',
            'firstbit'
        ))
        declarations.append({
            'kind': 'spi', 'id': bus, 'shared': True,
            'signature': signature,
            'name': 'max31865.spi',
        })
        for field in ('sck', 'mosi', 'miso'):
            _gpio(
                declarations, spi.get(field),
                'spi.' + str(bus) + '.' + field, shared=True
            )
        _gpio(declarations, spi.get('cs'), 'max31865.cs')

    voltage = device.get('ac_voltage')
    if isinstance(voltage, dict):
        pin = voltage.get('adc_pin')
        if pin is not None:
            declarations.append({
                'kind': 'adc', 'id': pin, 'name': 'ac_voltage.adc'
            })
            _gpio(declarations, pin, 'ac_voltage.adc.gpio')

    gpio = device.get('gpio')
    if isinstance(gpio, dict):
        for direction in ('input', 'output'):
            mapping = gpio.get(direction)
            if isinstance(mapping, dict):
                for name, pin in mapping.items():
                    _gpio(declarations, pin, 'gpio.' + direction + '.' + str(name))
                    if direction == 'output' and (device.get('type') or {}).get('class') == 'light' and subtype in ('rgb', 'brightness'):
                        declarations.append({'kind': 'pwm', 'id': pin, 'name': 'pwm.' + str(name)})

    return declarations


def validate_resources(devices, protected_pins=None, protected_display=None):
    manager = ResourceManager(protected_pins=protected_pins)
    errors = []
    if protected_display and protected_display.get('enabled'):
        from display import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG, **protected_display)
        manager.reserve('spi', cfg['spi'], 'core')
        for field in ('sck', 'mosi', 'miso', 'cs', 'dc', 'rst', 'button_a', 'button_b'):
            pin = cfg.get(field)
            if isinstance(pin, int) and not isinstance(pin, bool):
                manager.reserve('gpio', pin, 'core')
    for device in devices or ():
        try:
            manager.reserve_device(device)
        except (ValueError, ResourceConflict) as exc:
            errors.append(str(exc))
    return errors, manager
