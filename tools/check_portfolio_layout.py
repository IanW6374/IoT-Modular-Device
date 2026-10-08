"""Offline Chromium layout checks; never contact an IoT device or HA instance.

Requires sibling HA repositories and a Chromium executable. Generates isolated
fixtures and desktop/mobile screenshots in --output (a new temporary directory
by default). No normal browser profile is opened.
"""

import argparse
import importlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import portal_settings_views
import web_portal_ui

REPORT_SCRIPT = r"""
window.addEventListener('load', () => setTimeout(() => {
  const failures=[];
  const fields=[...document.querySelectorAll('label input:not([type=checkbox]):not([type=radio]):not([type=hidden]),label select:not([multiple]),label textarea')];
  for(const field of fields){
    if(!field.getClientRects().length || field.tagName==='TEXTAREA')continue;
    const height=field.getBoundingClientRect().height;
    if(Math.abs(height-42)>1)failures.push('Field height '+field.name+': '+height);
    if(getComputedStyle(field).fontSize!=='14px')failures.push('Field type size '+field.name+': '+getComputedStyle(field).fontSize);
  }
  for(const checkbox of document.querySelectorAll('label input[type=checkbox]')){
    const label=checkbox.closest('label');
    if(label.firstElementChild!==checkbox)failures.push('Checkbox follows text: '+checkbox.name);
  }
  for(const grid of document.querySelectorAll('.grid,.form-grid,.filter-grid')){
    const labels=[...grid.children].filter(node=>node.tagName==='LABEL'&&node.querySelector('input:not([type=checkbox]):not([type=hidden]),select'));
    for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++){
      if(Math.abs(labels[i].getBoundingClientRect().top-labels[j].getBoundingClientRect().top)>1)continue;
      const a=labels[i].querySelector('input,select'),b=labels[j].querySelector('input,select');
      if(Math.abs(a.getBoundingClientRect().top-b.getBoundingClientRect().top)>1)failures.push('Misaligned fields: '+a.name+' / '+b.name);
    }
  }
  if(document.documentElement.scrollWidth>innerWidth+1)failures.push('Page overflows viewport');
  const report=document.createElement('pre');report.id='layout-report';report.hidden=true;
  report.textContent=JSON.stringify({fields:fields.length,failures});document.body.append(report);
},100));
"""


def fixture(title, css, form, requirements):
    return ('<!doctype html><html><head><meta name="viewport" content="width=device-width">'
            '<meta charset="utf-8"><style>' + css + '</style></head><body><main>'
            '<section class="hero page-head"><h1>' + title + '</h1></section>' + form +
            '</main><script>' + requirements + '</script><script>' + REPORT_SCRIPT + '</script></body></html>')


def fixtures():
    siblings = ROOT.parent
    md_script = web_portal_ui.PORTAL_JS.split('/* Required/optional labels shared', 1)[1]
    md_script = '/* Required/optional labels shared' + md_script
    api = portal_settings_views.render_device_api_page('test', {'api_enabled': True, 'api_port': 8444})
    api = api.split('<main', 1)[1].split('>', 1)[1].split('</main>', 1)[0]
    yield 'device-api', fixture('Device API', web_portal_ui.PORTAL_CSS, api, md_script)
    network = portal_settings_views.render_settings_page('test', {'device_name': 'IoT-MD-001', 'description': 'Boiler', 'dhcp': True})
    network = network.split('<main', 1)[1].split('>', 1)[1].split('</main>', 1)[0]
    yield 'device-network', fixture('Network settings', web_portal_ui.PORTAL_CSS, network, md_script)

    management = siblings / 'HA-IoT-MD-Management-Suite/iot_md_management/rootfs/app'
    sys.path.insert(0, str(management))
    html = importlib.import_module('management_portal').HTML
    css = html.split('<style>', 1)[1].split('</style>', 1)[0]
    form = ('<section class="panel"><form><div class="grid">'
            '<label>Name<input name="name" value="HTW" required></label>'
            '<label>Description<input name="description" value="Hot water"></label>'
            '<label>Hostname<input name="host" value="iot-md-002.local" required></label>'
            '<label>Port<input name="port" type="number" value="8444" required></label>'
            '<label>Group<select name="cohort" required><option>default</option></select></label>'
            '<label class="check"><input name="enabled" type="checkbox" checked><span>Enable management</span></label>'
            '</div></form></section>')
    yield 'management-device', fixture('Device settings', css, form, (management / 'assets/form_requirements.js').read_text())

    ca = siblings / 'HA-IoT-Certificate-Authority/iot_certificate_authority/rootfs/opt/iot-ca/iot_ca/static'
    css = (ca / 'app.css').read_text() + (ca / 'form_controls.css').read_text()
    form = ('<section class="panel"><form class="form-grid"><div class="grid two">'
            '<label>Common name<input name="cn" required value="iot-md-001.local"></label>'
            '<label>Profile<select name="profile"><option>Portal server</option></select></label></div>'
            '<label class="check"><input type="checkbox" name="approved" required>Approve certificate request</label>'
            '</form></section>')
    yield 'certificate-form', fixture('Create certificate', css, form, (ca / 'form_requirements.js').read_text())

    syslog = siblings / 'HA-IoT-Syslog/iot_syslog/rootfs/app/static'
    css = (syslog / 'styles.css').read_text() + (syslog / 'form_controls.css').read_text()
    form = ('<section class="panel"><form class="filter-grid">'
            '<label class="search-field">Search events<input name="q" value="API"></label>'
            '<label>Device<select name="hostname"><option>All devices</option></select></label>'
            '<label>Severity<select name="severity"><option>All severities</option></select></label>'
            '<label>Transport<select name="transport"><option>All transports</option></select></label>'
            '</form></section>')
    yield 'syslog-filters', fixture('Events', css, form, (syslog / 'form_requirements.js').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or Path(tempfile.mkdtemp(prefix='iot-portfolio-layout-'))
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    for name, html in fixtures():
        path = output / (name + '.html')
        path.write_text(html)
        for width in (1280, 390):
            with tempfile.TemporaryDirectory(prefix='iot-ui-browser-') as profile:
                command = [args.browser, '--headless', '--disable-gpu', '--no-first-run',
                           '--no-default-browser-check', '--disable-background-networking',
                           '--user-data-dir=' + profile, '--window-size=' + str(width) + ',1100',
                           '--virtual-time-budget=1500', '--dump-dom',
                           '--screenshot=' + str(output / (name + '-' + str(width) + '.png')), path.as_uri()]
                try:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError('Headless browser did not finish for ' + name + ': ' +
                                       (exc.stderr or b'').decode(errors='replace')[-1500:]) from None
                report = re.search(r'<pre id="layout-report" hidden="">(.*?)</pre>', result.stdout)
                if result.returncode or not report:
                    raise RuntimeError('Browser check failed for ' + name + ': ' + result.stderr[-1500:])
                data = json.loads(report[1])
                print(name, width, data)
                failures.extend(name + ': ' + failure for failure in data['failures'])
    print('Screenshots:', output)
    if failures:
        raise SystemExit('\n'.join(failures))


if __name__ == '__main__':
    main()
