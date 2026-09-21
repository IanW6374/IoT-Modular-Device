#!/usr/bin/env python3
"""Optional Playwright regression: python3 tests/browser_upgrade_workflow.py.

Requires Playwright and Chromium, or CHROME_BIN pointing to a local browser.
Serves only local fixtures with the production portal Content Security Policy.
Screenshots are written under the ignored build directory.
"""
import os
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal_live_views as views
import portal_http
import web_portal_ui as ui
from playwright.sync_api import sync_playwright

STATUS = {
    'update_history': [{'time': 1700000000, 'event': 'confirmed', 'kind': 'universal', 'version': '3.0.0-alpha.34'}],
    'release_check_history': [{'time': 1700001000, 'event': 'Release available', 'kind': 'automatic check', 'version': '3.0.0-alpha.35'}],
    'release_checks_enabled': True, 'update_status': 'idle',
    'firmware_update_supported': True, 'firmware_update_status': 'idle',
    'firmware_update_availability': 'ready', 'previous_slot': 'a',
    'previous_slot_version': '3.0.0-alpha.32',
    'release_available_version': '3.0.0-alpha.34',
    'release_available_type': 'universal',
    'release_available_options': [
        {'version': '3.0.0-alpha.34', 'type': 'universal', 'release_sequence': 2739},
        {'version': '3.0.0-alpha.33', 'type': 'application', 'release_sequence': 2738},
    ],
}
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlsplit(self.path)
        query = parse_qs(path.query)
        headers = ()
        content_type = 'text/html; charset=utf-8'
        if path.path == '/assets/portal.css':
            body, content_type = ui.PORTAL_CSS, 'text/css'
        elif path.path == '/assets/portal.js':
            body, content_type = ui.PORTAL_JS, 'application/javascript'
        elif path.path.startswith('/api/'):
            body, content_type = '{}', 'application/json'
        elif path.path == '/task-status':
            body, content_type = json.dumps({'phase': 'complete', 'message': 'Release available'}), 'application/json'
        else:
            status = dict(STATUS)
            if query.get('fixture') == ['staged']:
                status.update(universal_update_status='ready', universal_update_version='3.0.0-alpha.34',
                              update_status='ready', firmware_update_status='ready')
            if query.get('fixture') == ['empty']:
                status.pop('previous_slot')
                status.pop('release_available_version')
                status.pop('release_available_options')
            body = views.render_updates_page('test-csrf', status, source=query.get('source', [''])[0])
            if path.path == '/release-qualification':
                body = views.render_release_qualification_page('test-csrf', {
                    'available': True, 'summary': 'Blocked', 'retry_generation': 0,
                    'evidence': {'gates': [{'name': 'health', 'status': 'failed', 'observed': 200, 'required': 2400},
                                           {'name': 'storage', 'status': 'passed', 'observed': 2400, 'required': 2400}]},
                })
            body = body.replace('<!--session-timeout-->', '3600000')
            body, headers = portal_http.secure_html_response(body, (), 'test-nonce')
        data = body.encode()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', '0')))
        data = b'{"task_id":"check-1"}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:' + str(server.server_port)
Path('build').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('CHROME_BIN'), headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1080})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if 'Content Security Policy' in message.text else None)
    for width in (2048, 1440, 1024, 768, 390):
        page.set_viewport_size({'width': width, 'height': 1080})
        for route in ('/updates', '/updates?source=manual', '/updates?source=automatic',
                      '/updates?source=rollback', '/updates?fixture=staged'):
            page.goto(base + route)
            page.wait_for_selector('.upgrade-stage-ring')
            assert page.locator('h1').inner_text() == 'Upgrade'
            assert page.get_by_role('heading', name='Upgrade history', exact=True).is_visible()
            assert page.locator('#upgrade-check-result').count() == 1
            assert page.locator('#upgrade-check-result').evaluate('''(badge)=>{
                const card=badge.parentElement, title=card.querySelector('strong');
                const b=badge.getBoundingClientRect(), t=title.getBoundingClientRect();
                const c=card.getBoundingClientRect();
                return Math.abs(b.top-t.top)<2 && Math.abs(c.right-b.right-15)<2 && b.left>=t.right;
            }'''), (width, route, 'badge not top right')
            assert page.locator('.metric.update-status').count() == 0
            rings = page.locator('.upgrade-stage-ring').evaluate_all('(els)=>els.map(e=>({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y}))')
            assert len({round(r['y']) if width > 600 else round(r['x']) for r in rings}) == 1, (width, route, rings)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, route, 'overflow')
            assert page.locator('.upgrade-steps-panel').evaluate('(e)=>e.scrollWidth<=e.clientWidth'), (width, route, 'track overflow')
            assert page.locator('.upgrade-operation').evaluate('(e)=>Array.from(e.querySelectorAll("button")).every(b=>b.getBoundingClientRect().bottom<=e.closest("section").getBoundingClientRect().bottom)'), (width, route, 'action outside card')
        print('CSP layout passed at', width, flush=True)
    page.set_viewport_size({'width': 1440, 'height': 1080})
    page.goto(base + '/updates?source=manual')
    page.locator('#update-bundle').set_input_files({'name':'universal.iotuni', 'mimeType':'application/octet-stream','buffer':b'test'})
    assert page.locator('#update-stage-list li').count() == 10
    assert page.locator('#update-primary').inner_text() == 'Stage upgrade'
    assert page.locator('#update-primary').is_enabled()
    page.evaluate('setMilestone(document.querySelector("#update-stage-list li.active"),"active",42)')
    assert page.locator('#update-stage-list li.active .upgrade-stage-percent').inner_text() == '42%'
    assert '42%' in page.locator('#update-stage-list li.active .upgrade-stage-ring').evaluate('(e)=>getComputedStyle(e).backgroundImage')
    page.screenshot(path='build/alpha34-manual-desktop.png', full_page=True)
    page.locator('#update-cancel').click()
    assert page.locator('#update-primary').is_disabled()
    page.goto(base + '/updates?source=automatic')
    assert page.locator('#automatic-stage-list li').count() == 10
    page.locator('#automatic-release-version-select').select_option('3.0.0-alpha.33')
    assert page.locator('#automatic-stage-list li').count() == 6
    page.locator('#automatic-release-version-select').select_option('3.0.0-alpha.34')
    page.screenshot(path='build/alpha34-automatic-desktop.png', full_page=True)
    with page.expect_navigation():
        page.get_by_role('button', name='Check for upgrades', exact=True).click()
    page.goto(base + '/updates?fixture=staged')
    assert page.get_by_role('link', name='Staged', exact=False).count() == 1
    assert page.locator('.upgrade-stage-list li').count() == 10
    assert page.locator('.upgrade-stage-list li.complete').count() == 9
    assert '100%' in page.locator('.upgrade-stage-list li.complete .upgrade-stage-ring').first.evaluate('(e)=>getComputedStyle(e).backgroundImage')
    page.screenshot(path='build/alpha34-staged-desktop.png', full_page=True)
    page.goto(base + '/updates?fixture=empty')
    assert page.locator('.upgrade-method-choice').count() == 2
    page.get_by_role('link', name='Automatic', exact=False).click()
    assert page.get_by_role('button', name='Check for upgrades').count() == 1
    page.set_viewport_size({'width':390, 'height':844})
    page.goto(base + '/updates?source=automatic')
    page.screenshot(path='build/alpha34-automatic-mobile.png', full_page=True)
    for width in (1440, 390):
        page.set_viewport_size({'width':width, 'height':1080})
        page.goto(base + '/release-qualification')
        page.get_by_text('Restart failed test', exact=True).click()
        form = page.locator('form[action="/restart-qualification-gate"]')
        assert not form.evaluate('(e)=>e.checkValidity()')
        form.get_by_label('Reason for retry').fill('MQTT configuration corrected')
        form.locator('input[name="confirm"]').check()
        assert form.evaluate('(e)=>e.checkValidity()')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path='build/alpha35-qualification-'+str(width)+'.png', full_page=True)
    assert not errors, errors
    browser.close()
server.shutdown()
print('Upgrade controls and CSP checks passed')
