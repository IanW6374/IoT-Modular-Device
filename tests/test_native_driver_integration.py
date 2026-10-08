"""Owner-bound driver wiring, without constructing host or live peripherals."""
import sys
import types
import unittest
from unittest import mock

from device_modules.resources import ResourceManager, validate_resources
from device_modules.native_resources import NativeObject
from device_modules.managed_setup import setup_driver
from device_modules.driver_index import DRIVER_MODULES


class Provider:
    ABI_VERSION = 7
    def __init__(self):
        self.claims, self.objects = {}, {}
        self.next = 0
        self.fail = None
        self.calls = []

    def resource_claim(self, kind, key, owner, shared, signature):
        self.next += 1
        self.claims[self.next] = (kind, key, owner, shared, signature)
        return self.next

    def resource_object(self, handle, parameters):
        if self.claims[handle][0] == self.fail:
            raise OSError('injected construction failure')
        self.objects[handle] = dict(parameters)
        return True

    def resource_call(self, handle, name, args, kwargs):
        if handle not in self.claims:
            raise OSError('released handle')
        self.calls.append((handle, name, args, kwargs))
        return 0

    def resource_sensor(self, handle, name, *args):
        if handle not in self.claims:
            raise OSError('released handle')
        return (20, 40) if name == 'dht11' else 100

    def resource_release_owner(self, owner):
        for handle in tuple(self.claims):
            if self.claims[handle][2] == owner:
                self.claims.pop(handle)
                self.objects.pop(handle, None)


class NativeDriverIntegrationTests(unittest.TestCase):
    def setUp(self):
        class Pin:
            IN, OUT, PULL_UP = 0, 1, 2
            def __init__(self, *_args, **_kwargs):
                raise AssertionError('unmanaged Pin construction')
        patches = mock.patch.dict(sys.modules, {
            'machine': types.SimpleNamespace(Pin=Pin),
            'primitives': types.SimpleNamespace(Pushbutton=lambda pin: pin),
            'uhcsr04.hcsr04': types.SimpleNamespace(HCSR04=lambda *args, **kw: kw),
        })
        patches.start()
        self.addCleanup(patches.stop)

    def device(self, kind, owner='module-1'):
        cls, subtype = kind.split(':')
        return {'uuid': owner, 'type': {'class': cls, 'subclass': subtype},
            'gpio': {'input': {'0': 2, 'clk': 3, 'dt': 4, 'sw': 5, 'trig': 6, 'echo': 7},
                'output': {'0': 8, 'r': 9, 'g': 10, 'b': 11}, 'pwm_freq': 1000}}

    def manager(self, devices):
        errors, manager = validate_resources(devices)
        self.assertEqual(errors, [])
        provider = Provider()
        manager.enable_native(provider)
        return manager, provider

    def test_every_packaged_type_has_native_wiring(self):
        for kind in DRIVER_MODULES:
            with self.subTest(kind=kind):
                device = self.device(kind)
                if kind not in ('sensor:dht11', 'sensor:hcsr04') and not kind.startswith(('light:', 'switch:')):
                    device.pop('gpio')
                manager, provider = self.manager([device])
                module = types.SimpleNamespace(EMSBoilerDriver=lambda _device, _char: object())
                result = setup_driver(module, device, 1, manager.scope(device['uuid']))
                self.assertEqual(result['uuid'], device['uuid'])
                self.assertTrue(provider.objects)
                self.assertTrue(all(value[2] == device['uuid'] for value in provider.claims.values()))

    def test_old_proxy_cannot_use_new_owner_handle(self):
        manager = ResourceManager()
        provider = Provider()
        manager.reserve('gpio', 2, 'old')
        manager.enable_native(provider)
        old = manager.scope('old').pin(2)
        manager.release_owner('old')
        manager.reserve('gpio', 2, 'new')
        new = manager.scope('new').pin(2)
        self.assertNotEqual(old.handle, new.handle)
        with self.assertRaises(OSError):
            old.value(1)
        new.value(1)

    def test_cross_owner_and_undeclared_construction_fail(self):
        manager, _ = self.manager([self.device('sensor:EMS-Boiler')])
        with self.assertRaisesRegex(RuntimeError, 'undeclared'):
            manager.scope('intruder').construct('uart', 1)

    def test_configuration_is_immutable_for_owner(self):
        manager = ResourceManager()
        manager.reserve('gpio', 2, 'owner')
        manager.enable_native(Provider())
        manager.scope('owner').pin(2, mode=0)
        with self.assertRaisesRegex(RuntimeError, 'configuration changed'):
            manager.scope('owner').pin(2, mode=1)

    def test_single_port_declared_defaults_match_native_construction(self):
        device = self.device('sensor:RS485-Modbus')
        device.pop('gpio')
        device['rs485'] = {'ports': {'inverter': {'baudrate': 19200}}}
        manager, provider = self.manager([device])
        result = setup_driver(None, device, 0, manager.scope(device['uuid']))
        uart = result['ports']['ch0']['uart']
        self.assertEqual(provider.objects[uart.handle]['baudrate'], 19200)
        self.assertEqual(provider.objects[uart.handle]['tx'], 17)
        self.assertEqual(provider.objects[uart.handle]['rx'], 18)

    def test_multiport_default_wiring_keeps_configured_baudrate(self):
        device = self.device('sensor:RS485-Modbus-Multiport')
        device.pop('gpio')
        device['baudrate'] = 19200
        manager, provider = self.manager([device])
        result = setup_driver(None, device, 0, manager.scope(device['uuid']))
        self.assertEqual(provider.objects[result['ports']['ch0']['uart'].handle]['baudrate'], 19200)

    def test_multiport_implicit_machine_pins_are_rejected_before_hardware(self):
        device = self.device('sensor:RS485-Modbus-Multiport')
        device.pop('gpio')
        device['rs485'] = {'ports': {'ch0': {'uart': 1}}}
        errors, _ = validate_resources([device])
        self.assertIn('explicit TX and RX', ';'.join(errors))

    def test_shared_spi_retains_remaining_owner(self):
        first = self.device('sensor:MAX31865-PT1000', 'first')
        second = self.device('sensor:MAX31865-PT1000', 'second')
        second['max31865'] = {'cs': 6}
        # Only relevant declared GPIOs; unrelated fixture maps are removed.
        first.pop('gpio'); second.pop('gpio')
        manager, provider = self.manager([first, second])
        a = setup_driver(None, first, 0, manager.scope('first'))
        b = setup_driver(None, second, 1, manager.scope('second'))
        manager.release_owner('first')
        with self.assertRaises(OSError):
            a['spi'].write(b'1')
        b['spi'].write(b'1')
        self.assertTrue(all(value[2] == 'second' for value in provider.claims.values()))

    def test_core_led_conflict_is_rejected_before_hardware(self):
        device = self.device('light:onoff')
        errors, _ = validate_resources([device], protected_pins=[8])
        self.assertIn('core', ';'.join(errors))

    def test_unknown_methods_do_not_fake_attribute_support(self):
        proxy = NativeObject(Provider(), 1, 'uart')
        self.assertIsNone(getattr(proxy, 'IRQ_BREAK', None))
        self.assertFalse(hasattr(proxy, 'init'))

    def test_irq_callback_never_exposes_raw_uart(self):
        provider = Provider()
        provider.claims[1] = ('uart', 'uart:1', 'owner', False, '')
        proxy = NativeObject(provider, 1, 'uart')
        callback = mock.Mock()
        proxy.irq(handler=callback, trigger=1)
        kwargs = provider.calls[-1][3]
        kwargs['handler'](object())
        callback.assert_called_once_with(proxy)
        self.assertFalse(kwargs['hard'])

    def test_encoder_gpio_irqs_remain_soft_and_ignore_released_pins(self):
        provider = Provider()
        provider.claims[1] = ('gpio', 'gpio:2', 'owner', False, '')
        proxy = NativeObject(provider, 1, 'gpio')
        callback = mock.Mock()
        proxy.irq(handler=callback, trigger=3, hard=True)
        kwargs = provider.calls[-1][3]
        self.assertNotIn('hard', kwargs)  # ESP32 Pin IRQ is always scheduled.
        kwargs['handler'](object())
        callback.assert_called_once_with(proxy)
        provider.resource_release_owner('owner')
        kwargs['handler'](object())
        callback.assert_called_once_with(proxy)

    def test_wrong_core_cannot_fall_back_to_machine(self):
        provider = Provider(); provider.ABI_VERSION = 6
        with self.assertRaisesRegex(RuntimeError, 'ABI 7'):
            ResourceManager().enable_native(provider)

    def test_failed_driver_setup_releases_all_owned_resources(self):
        from device_modules import loader
        device = self.device('light:brightness')
        manager, provider = self.manager([device])
        provider.fail = 'pwm'
        module = types.SimpleNamespace(supports=lambda _device: True)
        with mock.patch.object(loader, '_MODULES', [module]), mock.patch.object(loader, '_RESOURCE_MANAGER', manager):
            result = loader.setup_device(device, 0)
        self.assertIn('injected construction failure', result['setup_error'])
        self.assertFalse(provider.claims)
        self.assertFalse(provider.objects)

    def test_incompatible_shared_bus_is_rejected_before_construction(self):
        first = self.device('sensor:MAX31865-PT1000', 'first')
        second = self.device('sensor:MAX31865-PT1000', 'second')
        first.pop('gpio'); second.pop('gpio')
        second['max31865'] = {'cs': 6, 'baudrate': 2000000}
        errors, _ = validate_resources([first, second])
        self.assertIn('incompatible', ';'.join(errors))
