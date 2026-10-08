"""Shipped-driver wiring. Production never constructs unowned peripherals."""


def setup_driver(module, device, index, resources):
    from machine import Pin
    kind = device['type']['subclass']
    result = {'uuid': device['uuid'], 'index': index}
    gpio = device.get('gpio', {})
    inputs = gpio.get('input', {})
    if kind in ('onoff', 'brightness', 'rgb') and device['type']['class'] == 'light':
        inactive = 0 if gpio.get('activeHigh', True) else 1
        outputs = {}
        for channel, number in gpio.get('output', {}).items():
            if kind == 'onoff':
                outputs[channel] = resources.pin(number, Pin.OUT, value=inactive)
            else:
                outputs[channel] = resources.construct('pwm', number,
                    freq=gpio.get('pwm_freq', 1000), duty_u16=65535 * inactive)
        result['output'] = outputs
    elif device['type']['class'] == 'switch':
        from primitives import Pushbutton
        if kind == 'onoff':
            number = inputs['0']
            result.update(gpio={0: number}, input={
                '0': Pushbutton(resources.pin(number, Pin.IN, Pin.PULL_UP))})
        else:
            result.update(gpio={0: inputs['sw']}, input={
                'clk': resources.pin(inputs['clk'], Pin.IN, Pin.PULL_UP),
                'dt': resources.pin(inputs['dt'], Pin.IN, Pin.PULL_UP),
                'sw': Pushbutton(resources.pin(inputs['sw'], Pin.IN, Pin.PULL_UP))})
    elif kind == 'dht11':
        from .native_resources import NativeDHT
        result['input'] = {0: NativeDHT(resources.pin(inputs['0'], Pin.IN))}
    elif kind == 'hcsr04':
        from uhcsr04.hcsr04 import HCSR04
        trigger = resources.pin(inputs['trig'], Pin.OUT, value=0)
        echo = resources.pin(inputs['echo'], Pin.IN)
        result['input'] = {0: HCSR04(inputs['trig'], inputs['echo'], 10000,
            trigger=trigger, echo=echo, pulse_reader=echo.pulse_us)}
    elif kind == 'Grove-AC-Voltage':
        cfg = device.get('ac_voltage', {})
        attenuation = {0: 0, 2: 1, 6: 2, 11: 3}.get(int(cfg.get('atten_db', 11)))
        if attenuation is None:
            raise ValueError('unsupported ESP32 ADC attenuation')
        result['adc'] = resources.construct('adc',
            cfg.get('adc_pin', device.get('adc_pin', 1)), atten=attenuation)
    elif kind == 'MAX31865-PT1000':
        cfg = dict({'spi': 1, 'sck': 2, 'mosi': 3, 'miso': 4, 'cs': 5,
            'baudrate': 1000000, 'polarity': 0, 'phase': 1, 'bits': 8,
            'firstbit': 0}, **device.get('max31865', {}))
        result['spi'] = resources.construct('spi', cfg['spi'], **{
            key: cfg[key] for key in ('sck', 'mosi', 'miso', 'baudrate',
                'polarity', 'phase', 'bits', 'firstbit')})
        result['cs'] = resources.pin(cfg['cs'], Pin.OUT, value=1)
    elif kind == 'EMS-Boiler':
        cfg = dict({'uart': 1, 'tx': 17, 'rx': 18}, **device.get('ems', {}))
        result['uart'] = _uart(resources, cfg)
        result['driver'] = module.EMSBoilerDriver(device, result)
    elif kind in ('WHES', 'RS485-Modbus', 'RS485-Modbus-Multiport'):
        rs485 = device.get('rs485', {})
        ports = rs485.get('ports')
        if not ports:
            cfg = dict({'uart': 1, 'tx': 17, 'rx': 18}, **rs485)
            if kind == 'RS485-Modbus-Multiport':
                cfg = {key: device.get(key, default) for key, default in
                    (('uart', 1), ('tx', 8), ('rx', 9), ('baudrate', 9600))}
            ports = {'ch0': cfg}
        if kind != 'RS485-Modbus-Multiport' and len(ports) != 1:
            raise ValueError('single-port RS485 requires exactly one port')
        result['ports'] = {}
        for name, config in ports.items():
            cfg = dict({'uart': 1, 'tx': 17, 'rx': 18}, **config)
            active = cfg.get('tx_enable_active', 1)
            result['ports'][name if kind == 'RS485-Modbus-Multiport' else 'ch0'] = {
                'uart': _uart(resources, cfg),
                'tx_enable': resources.pin(cfg['de'], Pin.OUT, value=0 if active else 1)
                    if cfg.get('de') is not None else None,
                'tx_enable_active': active, 'turnaround_ms': cfg.get('turnaround_ms', 5),
                'timeout_ms': cfg.get('timeout_ms', rs485.get('timeout_ms', 500)),
            }
    else:
        raise RuntimeError('packaged driver has no native resource wiring: ' + str(kind))
    return result


def _uart(resources, cfg):
    return resources.construct('uart', cfg['uart'], baudrate=cfg.get('baudrate', 9600),
        bits=cfg.get('bits', 8), parity=cfg.get('parity'), stop=cfg.get('stop', 1),
        tx=cfg['tx'], rx=cfg['rx'], timeout=0, timeout_char=0, rxbuf=4096)
