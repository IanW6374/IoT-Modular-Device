#!/usr/bin/env python3
"""Structural accessibility checks for rendered device portal HTML."""

from html.parser import HTMLParser
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicates = []
        self.images_without_alt = 0
        self.viewport = False
        self.language = False
        self.main = False
        self.inline_handlers = []
        self.unnonced_inline_scripts = 0
        self._script_src = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        identifier = values.get('id')
        if identifier in self.ids:
            self.duplicates.append(identifier)
        elif identifier:
            self.ids.add(identifier)
        if tag == 'img' and 'alt' not in values:
            self.images_without_alt += 1
        if tag == 'meta' and values.get('name') == 'viewport':
            self.viewport = True
        if tag == 'html' and values.get('lang'):
            self.language = True
        if tag == 'main' and values.get('id') == 'main-content':
            self.main = True
        for key, _value in attrs:
            if str(key).lower().startswith('on'):
                self.inline_handlers.append(key)
        if tag == 'script':
            self._script_src = bool(values.get('src'))
            if not self._script_src and not values.get('nonce'):
                self.unnonced_inline_scripts += 1


def check(name, html):
    audit = Audit()
    audit.feed(html)
    failures = []
    if audit.duplicates:
        failures.append(name + ': duplicate ids ' + ', '.join(audit.duplicates))
    if audit.images_without_alt:
        failures.append(name + ': image missing alt text')
    if not audit.viewport:
        failures.append(name + ': viewport metadata missing')
    if not audit.language:
        failures.append(name + ': document language missing')
    if not audit.main:
        failures.append(name + ': main-content landmark missing')
    if audit.inline_handlers:
        failures.append(name + ': inline event handlers are not CSP-safe')
    if audit.unnonced_inline_scripts:
        failures.append(name + ': inline script is missing a CSP nonce')
    return failures


def main():
    import web_portal
    import certificate_portal_views
    pages = {
        'portal overview': web_portal.render_page('csrf', 'INFO', ('INFO',), [], 5000),
        'portal upgrades': web_portal.render_updates_page('csrf'),
        'portal backup': web_portal.render_configuration_backup_page('csrf'),
        'portal users': web_portal.render_user_settings_page(
            'csrf', {}, users=({'username': 'admin', 'role': 'administrator', 'enabled': True},)
        ),
        'portal modules': web_portal.render_module_settings_page('csrf'),
        'portal certificates': certificate_portal_views.render_certificate_page('csrf'),
        'portal device control': web_portal.render_device_control_page('csrf'),
    }
    failures = []
    for name, html in pages.items():
        failures.extend(check(name, html))
    if failures:
        raise SystemExit('\n'.join(failures))
    css = web_portal.portal_ui.PORTAL_CSS
    script = web_portal.portal_ui.PORTAL_JS
    for marker in ('prefers-reduced-motion', 'prefers-color-scheme', 'forced-colors'):
        if marker not in css:
            failures.append('portal stylesheet: missing ' + marker)
    for marker in ('ArrowDown', 'Escape', 'portalAdaptivePoll'):
        if marker not in script:
            failures.append('portal script: missing ' + marker)
    if failures:
        raise SystemExit('\n'.join(failures))
    print('accessibility structure check passed')


if __name__ == '__main__':
    main()
