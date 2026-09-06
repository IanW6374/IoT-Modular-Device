"""Small module-action transport handlers for the authenticated portal."""

from portal_http import apply_portal_action
from portal_live_views import render_module_diagnostics_page


async def handle_calibration(
    action_path, form_params, action_handler, log_output, module_snapshot,
    csrf_token, value_refresh_ms, session_role, writer, send_response
):
    """Apply calibration and keep its durable outcome on the diagnostics page."""
    result = apply_portal_action(
        'calibrate', action_path, action_handler, log_output, form_params
    )
    notice = (
        result.get('message', '')
        if isinstance(result, dict) else str(result)
    )
    failed = 'failed' in notice.lower()
    module_snapshot.invalidate()
    await send_response(
        writer,
        '400 Bad Request' if failed else '200 OK',
        render_module_diagnostics_page(
            csrf_token, module_snapshot.get(), value_refresh_ms or 5000,
            session_role, notice, failed
        )
    )
