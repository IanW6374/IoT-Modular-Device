try:
    import ujson as json
except ImportError:
    import json


class ActionResponder:
    # Return JSON for in-place portal actions with classic HTML fallbacks.

    def __init__(
        self, headers, writer, send_response, send_redirect,
        restart_status_getter=None
    ):
        self.headers = headers
        self.writer = writer
        self.send_response = send_response
        self.send_redirect = send_redirect
        self.restart_status_getter = restart_status_getter

    def requested(self):
        return 'application/json' in str(
            self.headers.get('accept', '')
        ).lower()

    async def send(
        self, status, message='', error=False, html=None, redirect='', **extra
    ):
        if not self.requested():
            if redirect:
                await self.send_redirect(self.writer, redirect)
            else:
                await self.send_response(
                    self.writer, status,
                    html if html is not None else str(message)
                )
            return
        payload = {
            'ok': not error,
            'message': str(
                message or ('Request failed' if error else 'Changes saved')
            ),
        }
        if error:
            payload['error'] = payload['message']
        if self.restart_status_getter:
            try:
                payload['restart'] = self.restart_status_getter()
            except Exception:
                pass
        payload.update(extra)
        await self.send_response(
            self.writer, status, json.dumps(payload), 'application/json'
        )
