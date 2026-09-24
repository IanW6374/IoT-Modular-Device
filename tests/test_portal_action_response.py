import asyncio
import json
import unittest

from portal_action_response import ActionResponder


class PortalActionResponseTests(unittest.TestCase):
    def test_json_action_response_includes_restart_and_refresh_state(self):
        calls = []

        async def send_response(writer, status, body, content_type='text/html'):
            calls.append((writer, status, body, content_type))

        async def send_redirect(writer, location):
            raise AssertionError('JSON action must not redirect')

        responder = ActionResponder(
            {'accept': 'application/json'}, 'writer', send_response,
            send_redirect, lambda: {'required': True, 'reason_count': 1}
        )
        asyncio.run(responder.send(
            '200 OK', 'Saved', refresh_target='#workspace'
        ))

        writer, status, body, content_type = calls[0]
        self.assertEqual((writer, status, content_type),
                         ('writer', '200 OK', 'application/json'))
        self.assertEqual(json.loads(body), {
            'ok': True,
            'message': 'Saved',
            'restart': {'required': True, 'reason_count': 1},
            'refresh_target': '#workspace',
        })

    def test_classic_action_uses_html_or_redirect_fallback(self):
        responses = []
        redirects = []

        async def send_response(writer, status, body, content_type='text/html'):
            responses.append((writer, status, body, content_type))

        async def send_redirect(writer, location):
            redirects.append((writer, location))

        responder = ActionResponder(
            {'accept': 'text/html'}, 'writer', send_response, send_redirect
        )
        asyncio.run(responder.send(
            '400 Bad Request', 'Invalid', True, html='<p>Invalid</p>'
        ))
        asyncio.run(responder.send(
            '200 OK', 'Saved', redirect='/settings'
        ))

        self.assertEqual(
            responses, [('writer', '400 Bad Request', '<p>Invalid</p>', 'text/html')]
        )
        self.assertEqual(redirects, [('writer', '/settings')])


if __name__ == '__main__':
    unittest.main()
