"""Recoverable MQTT startup independent of device boot health."""


class MQTTStartupService:
    def __init__(self, client, configure, publish_worker, connection_handlers,
                 start_task, state, log_output, sleep, error_detail):
        self.client = client
        self.configure = configure
        self.publish_worker = publish_worker
        self.connection_handlers = tuple(connection_handlers)
        self.start_task = start_task
        self.state = state
        self.log_output = log_output
        self.sleep = sleep
        self.error_detail = error_detail

    async def connect(self):
        try:
            await self._activate()
        except (ValueError, OSError) as exc:
            self.state.set('mqtt', 'retrying')
            self.log_output(
                'MQTT', 'Connect',
                {'log': 'Connection unavailable: ' + self.error_detail(exc)},
                'WARNING'
            )
            self.start_task('mqtt_startup_retry', self.retry())
            return False
        return True

    async def _activate(self):
        if not self.client.isconnected():
            await self.client.connect()
        self.client.up.clear()
        await self.configure(self.client)
        self.start_task(
            'mqtt_publish_worker', self.publish_worker(), main_device_task=True
        )
        self.state.set('mqtt', 'online')
        for handler in self.connection_handlers:
            self.start_task(
                handler.__name__, handler(self.client), main_device_task=True
            )

    async def retry(self, initial_delay_s=5, maximum_delay_s=60):
        delay = max(1, int(initial_delay_s))
        while True:
            self.state.set('mqtt', 'retrying')
            await self.sleep(delay)
            try:
                await self._activate()
            except (ValueError, OSError) as exc:
                self.log_output(
                    'MQTT', 'Reconnect',
                    {'log': 'Retry failed: ' + self.error_detail(exc)},
                    'WARNING'
                )
                delay = min(maximum_delay_s, delay * 2)
            else:
                self.log_output(
                    'MQTT', 'Reconnect',
                    {'log': 'Broker connection recovered'}, 'INFO'
                )
                return
