"""HTTP adapter for certificate portal routes."""

from portal_http import apply_portal_action


def _render_certificate_route(*args, **kwargs):
    # These pages are comparatively large and are used only by administrators.
    # Import them on demand rather than during every device boot.
    from certificate_portal_views import render_certificate_route
    return render_certificate_route(*args, **kwargs)


async def handle(method, route, path, writer, reader, headers, form, csrf,
                 actions, log_output, upload, validate, inventory,
                 send_response, send_redirect):
    certificate_routes = (
        '/certificates', '/certificate-authorities',
        '/api-client-trust', '/device-certificates'
    )
    wants_json = 'application/json' in str(headers.get('accept', '')).lower()

    async def send_action(status, message, target, result=None):
        import json
        payload = {
            'ok': not str(status).startswith('4') and not str(status).startswith('5'),
            'message': str(message or 'Certificate settings updated'),
            'refresh_target': '#certificate-workspace',
            'refresh_url': target,
        }
        if isinstance(result, dict) and result.get('task_id'):
            payload['task_id'] = result['task_id']
        await send_response(writer, status, json.dumps(payload), 'application/json')
    if method == 'GET' and route in certificate_routes:
        await send_response(writer, '200 OK', _render_certificate_route(
            route, csrf, certificates=inventory() if inventory else {}
        ))
        return True
    if method == 'POST' and route == '/remove-certificate-trust':
        result = apply_portal_action(
            'remove-certificate-trust', path, actions, log_output, form
        )
        target = form.get('return_to', '/certificate-authorities')
        if target not in certificate_routes:
            target = '/certificate-authorities'
        message = result.get('message', '') if isinstance(result, dict) else str(result or '')
        if wants_json:
            await send_action('200 OK', message or 'Certificate trust removed', target, result)
        else:
            await send_redirect(writer, target)
        return True
    if method == 'POST' and route == '/certificate-method':
        result = apply_portal_action(
            'certificate-method', path, actions, log_output, form
        )
        message = result.get('message', '') if isinstance(result, dict) else result
        if wants_json:
            await send_action('202 Accepted', message, '/certificates', result)
        else:
            await send_response(writer, '202 Accepted', _render_certificate_route(
                '/certificates', csrf, message, inventory() if inventory else {}
            ))
        return True
    if method == 'POST' and route == '/renew-certificate':
        result = apply_portal_action(
            'renew-certificate', path, actions, log_output, form
        )
        message = result.get('message', '') if isinstance(result, dict) else result
        target = form.get('return_to', '/certificates')
        if target not in certificate_routes:
            target = '/certificates'
        if wants_json:
            await send_action('202 Accepted', message, target, result)
        elif isinstance(result, dict) and result.get('task_id'):
            await send_redirect(
                writer, '/task?id=' + str(result['task_id']) + '&return=' +
                target.lstrip('/')
            )
        else:
            await send_response(writer, '202 Accepted', _render_certificate_route(
                target, csrf, message, inventory() if inventory else {}
            ))
        return True
    if method == 'POST' and path.startswith('/certificate-upload'):
        if upload is None:
            await send_response(writer, '503 Service Unavailable', 'Certificate upload is unavailable', 'text/plain')
            return True
        length = int(headers.get('content-length', '0') or 0)
        if length <= 0 or length > 16384:
            raise ValueError('certificate file size is invalid')
        await upload(headers.get('x-certificate-kind', ''), reader, length)
        await send_response(writer, '200 OK', 'Certificate file stored', 'text/plain')
        return True
    if method == 'POST' and route == '/validate-certificates':
        try:
            if validate is None:
                raise RuntimeError('certificate validation is unavailable')
            result = validate()
        except Exception as exc:
            if wants_json:
                await send_action('400 Bad Request', str(exc), form.get('return_to', '/device-certificates'))
            else:
                await send_response(writer, '400 Bad Request', str(exc), 'text/plain')
        else:
            message = result.get('message', '') if isinstance(result, dict) else str(result)
            target = form.get('return_to', '/device-certificates')
            if target not in certificate_routes:
                target = '/device-certificates'
            if wants_json:
                await send_action('200 OK', message, target, result)
            else:
                await send_response(writer, '200 OK', _render_certificate_route(
                    target, csrf, message, inventory() if inventory else {}
                ))
        return True
    return False
