"""Production driver I/O through generation-checked, core-owned peripherals."""
try:
    import uhashlib as hashlib
    import ubinascii as binascii
except ImportError:
    import hashlib
    import binascii


class NativeObject:
    def __init__(self, provider, handle, kind):
        self.provider, self.handle, self.kind = provider, handle, kind

    def __getattr__(self, name):
        methods = {
            'gpio': ('value', 'on', 'off'), 'pwm': ('freq', 'duty', 'duty_u16'),
            'adc': ('read', 'read_u16', 'read_uv'),
            'uart': ('read', 'readinto', 'write', 'any', 'flush'),
            'spi': ('read', 'readinto', 'write', 'write_readinto'),
            'i2c': ('scan', 'readfrom', 'readfrom_into', 'writeto', 'readfrom_mem',
                    'readfrom_mem_into', 'writeto_mem'),
        }
        if name not in methods.get(self.kind, ()):
            raise AttributeError(name)
        def call(*args, **kwargs):
            return self.provider.resource_call(self.handle, name, args, kwargs)
        return call

    def __call__(self, value=None):
        return self.value() if value is None else self.value(value)

    def pulse_us(self, level, timeout):
        return self.provider.resource_sensor(self.handle, 'pulse', level, timeout)

    def irq(self, handler=None, hard=False, **kwargs):
        # The machine callback receives a raw UART; never pass it to a driver.
        def guarded_callback(_object):
            try:
                self.provider.resource_call(self.handle,
                    'value' if self.kind == 'gpio' else 'any', (), {})
            except (ValueError, OSError):
                return  # A queued soft interrupt outlived its released lease.
            handler(self)
        callback = None if handler is None else guarded_callback
        kwargs['handler'] = callback
        if self.kind == 'uart':
            kwargs['hard'] = False
        return self.provider.resource_call(self.handle, 'irq', (), kwargs)


class NativeDHT:
    def __init__(self, pin):
        self.pin = pin
        self.values = (None, None)

    def measure(self):
        self.values = self.pin.provider.resource_sensor(self.pin.handle, 'dht11')

    def temperature(self):
        return self.values[0]

    def humidity(self):
        return self.values[1]


class NativeBackend:
    def __init__(self, manager, provider=None):
        if provider is None:
            from v3.runtime.iotmd_next.platform import Platform
            provider = Platform().provider
        if getattr(provider, 'ABI_VERSION', None) != 7:
            raise RuntimeError('driver integration requires native ABI 7 / core API 15')
        if any(not hasattr(provider, name) for name in ('resource_object', 'resource_call', 'resource_sensor')):
            raise RuntimeError('native driver I/O provider is incomplete')
        self.manager, self.provider = manager, provider
        self.claims, self.objects = {}, {}

    def prepare(self, owner):
        """Reserve all dependencies before constructing the first object."""
        try:
            for key, resource in self.manager._resources.items():
                if owner not in resource['owners'] or (owner, key) in self.claims:
                    continue
                shared = resource['shared']
                signature = ''
                if shared:
                    signature = 'bus:' + binascii.hexlify(hashlib.sha256(
                        str(resource['signature']).encode()).digest()).decode()[:40]
                self.claims[owner, key] = self.provider.resource_claim(
                    resource['kind'], key, owner, shared, signature)
        except Exception:
            self.release_owner(owner)
            raise

    def construct(self, owner, kind, identifier, parameters):
        self.prepare(owner)
        key = kind + ':' + str(identifier)
        handle = self.claims.get((owner, key))
        if handle is None:
            raise RuntimeError('undeclared hardware resource ' + key)
        existing = self.objects.get((owner, key))
        if existing:
            if existing[0] != parameters:
                raise RuntimeError('hardware configuration changed for ' + key)
            return existing[1]
        if self.provider.resource_object(handle, parameters) is not True:
            raise RuntimeError('native hardware construction failed')
        value = NativeObject(self.provider, handle, kind)
        self.objects[owner, key] = (dict(parameters), value)
        return value

    def release_owner(self, owner):
        self.provider.resource_release_owner(owner)
        for key in tuple(self.claims):
            if key[0] == owner:
                self.claims.pop(key, None)
                self.objects.pop(key, None)
