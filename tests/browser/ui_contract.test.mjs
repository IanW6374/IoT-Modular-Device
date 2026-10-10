import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const {JSDOM}=require(process.env.IOT_UI_NODE_MODULES ? `${process.env.IOT_UI_NODE_MODULES}/jsdom` : 'jsdom');
const root=fileURLToPath(new URL('../..',import.meta.url));
const python=code=>execFileSync(process.env.PYTHON || 'python3',['-c',code],{cwd:root,encoding:'utf8'});
test('accepted background work stays informational rather than claiming completion',async()=>{
  const dom=new JSDOM('<main><form data-portal-async action="/start"><div class="actions"><button type="submit">Start</button></div></form></main>',{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  dom.window.fetch=async()=>({ok:true,status:200,text:async()=>JSON.stringify({task_id:'task',message:'Work requested'}),json:async()=>({})});
  dom.window.eval(python('import web_portal_ui;print(web_portal_ui.PORTAL_JS)'));
  doc.querySelector('form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
  await new Promise(resolve=>setTimeout(resolve,20));
  const out=doc.querySelector('[data-portal-form-status]');assert.match(out.className,/info/);assert.doesNotMatch(out.className,/success/);dom.window.close();
});
test('task page exposes interrupted reads and clears the warning on recovery',async()=>{
  const dom=new JSDOM(python("import web_portal_ui;print(web_portal_ui.task_page('task','Checking'))"),{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  dom.window.fetch=async()=>{throw Error('Offline')};
  dom.window.eval(python('import web_portal_ui;print(web_portal_ui.PORTAL_JS)'));
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  await new Promise(resolve=>setTimeout(resolve,20));
  assert.match(doc.getElementById('task-progress').className,/warning/);
  assert.match(doc.querySelector('#task-progress .status-text').textContent,/interrupted/);
  dom.window.fetch=async()=>({ok:true,status:200,json:async()=>({phase:'running',message:'Recovered',percent:30})});
  dom.window.poll();await new Promise(resolve=>setTimeout(resolve,20));
  assert.doesNotMatch(doc.getElementById('task-progress').className,/warning/);assert.match(doc.querySelector('#task-progress .status-text').textContent,/Recovered/);
  dom.window.fetch=async()=>({ok:true,status:200,json:async()=>({phase:'failed',message:'Rejected'})});
  dom.window.poll();await new Promise(resolve=>setTimeout(resolve,20));
  assert.equal(doc.getElementById('task-progress').getAttribute('role'),'alert');assert.equal(doc.getElementById('task-progress').getAttribute('aria-live'),'assertive');dom.window.close();
});
test('log-level rejection uses a red notice and restores the confirmed choice',async()=>{
  const dom=new JSDOM(python("from portal_live_views import render_logging_page;print(render_logging_page('csrf','INFO',['INFO','DEBUG'],[]))"),{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  dom.window.fetch=async()=>({ok:true,status:200,text:async()=>JSON.stringify({ok:false,error:'Permission denied'}),json:async()=>({})});
  dom.window.eval(python('import web_portal_ui;print(web_portal_ui.PORTAL_JS)'));dom.window.portalAdaptivePoll=()=>{};
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  const level=doc.getElementById('log-level'),initial=level.value;level.value=initial==='DEBUG'?'INFO':'DEBUG';
  doc.getElementById('log-level-form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
  await new Promise(resolve=>setTimeout(resolve,20));
  assert.equal(level.value,initial);assert.match(doc.getElementById('log-level-error').className,/error/);assert.equal(doc.getElementById('log-level-error').textContent,'Permission denied');dom.window.close();
});
test('warnings and errors have consistent severity and occupy their own row above action buttons',async()=>{
  const html=python("from portal_live_views import render_updates_page; print(render_updates_page('csrf',{'universal_upload_status':'prepared'}))");
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  dom.window.fetch=async()=>({ok:true,status:200,json:async()=>({})});
  const style=doc.createElement('style');style.textContent=python('import web_portal_ui;print(web_portal_ui.PORTAL_CSS)');doc.head.append(style);
  const warning=doc.querySelector('.upgrade-operation .portal-status.warning'),controls=doc.querySelector('.manual-upgrade-buttons');
  assert.ok(warning);assert.ok(warning.compareDocumentPosition(controls)&dom.window.Node.DOCUMENT_POSITION_FOLLOWING);
  assert.equal(controls.parentElement.className,'card');
  dom.window.eval(python('import web_portal_ui;print(web_portal_ui.PORTAL_JS)'));
  const actions=doc.createElement('div');actions.className='actions';
  const out=doc.createElement('span');out.className='portal-status error';actions.append(out);doc.querySelector('main').append(actions);
  dom.window.portalStatus(out,'error','Rejected action');
  assert.equal(out.getAttribute('role'),'alert');assert.equal(out.getAttribute('aria-live'),'assertive');
  assert.equal(dom.window.getComputedStyle(out).flexBasis,'100%');assert.equal(dom.window.getComputedStyle(out).order,'-1');
  dom.window.portalStatus(out,'warning','Retrying status read');assert.equal(out.getAttribute('role'),'status');
  assert.equal(out.getAttribute('aria-live'),'polite');
  dom.window.close();
});
test('overview read failures show stale warning and recover without replacing retained values with errors',async()=>{
  const html=python("from portal_live_views import render_overview_page;print(render_overview_page('csrf',{},[]))");
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  let poll;dom.window.fetch=async()=>{throw Error('Offline')};
  dom.window.eval(python('import web_portal_ui;print(web_portal_ui.PORTAL_JS)'));
  dom.window.portalAdaptivePoll=callback=>{poll=callback};
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  poll();await new Promise(resolve=>setTimeout(resolve,20));
  assert.match(doc.getElementById('portal-poll-overview').textContent,/Showing last data/);
  assert.match(doc.getElementById('overview-refresh').className,/warn/);
  dom.window.fetch=async()=>({ok:true,status:200,json:async()=>({status:'<div id="overview-status">Fresh</div>',modules:'<div id="overview-modules">Fresh modules</div>'})});
  poll();await new Promise(resolve=>setTimeout(resolve,20));
  assert.equal(doc.getElementById('portal-poll-overview'),null);assert.equal(doc.getElementById('overview-status').textContent,'Fresh');
  assert.match(doc.getElementById('overview-refresh').className,/good/);dom.window.close();
});
test('HTTP 200 with an explicit rejected action cannot show success or discard unsaved values',async()=>{
  const dom=new JSDOM('<main><form data-portal-async data-portal-dirty action="/save"><input name="description" value="Original"><div class="actions"><button type="submit">Save</button></div></form></main>',{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  dom.window.fetch=async()=>({ok:true,status:200,text:async()=>JSON.stringify({ok:false,error:'Permission denied'})});
  dom.window.eval(python('import web_portal_ui;print(web_portal_ui.PORTAL_JS)'));
  const input=doc.querySelector('input');input.value='Unsaved';input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  doc.querySelector('form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
  await new Promise(resolve=>setTimeout(resolve,20));
  const out=doc.querySelector('[data-portal-form-status]');assert.match(out.className,/error/);assert.equal(out.textContent,'Permission denied');
  assert.equal(input.defaultValue,'Original');assert.equal(input.value,'Unsaved');assert.equal(doc.querySelector('form').dataset.portalDirty,'1');
  dom.window.close();
});
test('module configuration is readable immediately, discard stays formatted and invalid JSON cannot submit',()=>{
  const html=python(`from portal_settings_views import render_module_settings_page
print(render_module_settings_page('csrf','{"devices":[{"name":"Probe","entities":{"0":{"unit":"C"}}}]}'))`);
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://device.local',pretendToBeVisual:true}),doc=dom.window.document;
  dom.window.fetch=async()=>({ok:true,json:async()=>({})});
  dom.window.eval(python('import web_portal_ui; print(web_portal_ui.PORTAL_JS)'));
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  const raw=doc.getElementById('module-settings-json'),form=raw.form;
  assert.equal(raw.value,JSON.stringify(JSON.parse(raw.value),null,2));
  assert.match(raw.value,/\n  "devices":/);
  assert.equal(raw.defaultValue,raw.value);
  raw.value='{"bad":';
  const submit=new dom.window.Event('submit',{cancelable:true});
  form.onsubmit(submit);assert.equal(submit.defaultPrevented,true);
  assert.match(doc.querySelector('[data-portal-form-status]').textContent,/Invalid JSON/);
  form.reset();assert.equal(raw.value,raw.defaultValue);
  dom.window.close();
});
test('Overview and Users are primary links; nested Settings and Certificates preserve breadcrumbs',()=>{
  const html=python("import web_portal_ui; print(web_portal_ui.shell('Certificates','api_client_trust','', 'csrf'))");
  const dom=new JSDOM(html,{runScripts:'outside-only',pretendToBeVisual:true}),doc=dom.window.document;
  const nav=doc.querySelector('#portal-nav');
  assert.equal(nav.querySelector(':scope>a[href="/"]').textContent,'Overview');
  assert.equal(nav.querySelector(':scope>a[href="/user"]').textContent,'Users');
  assert.equal(nav.querySelector('[aria-label="Maintenance submenu"] a[href="/certificates"]'),null);
  const settings=nav.querySelector('[aria-label="Device submenu"] [aria-label="Settings submenu"]');
  assert.equal(settings.querySelectorAll('a').length,7);
  assert.equal(settings.querySelector('a[href="/update-settings"]').textContent,'Updates');
  assert.equal(settings.parentElement.classList.contains('open'),true);
  assert.deepEqual([...doc.querySelectorAll('.breadcrumb a')].map(a=>a.textContent),['Device','Settings','Certificates','API client trust']);
  dom.window.fetch=async()=>({ok:true,json:async()=>({})});
  dom.window.eval(python('import web_portal_ui; print(web_portal_ui.PORTAL_JS)'));
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  const trigger=settings.querySelector('.nav-submenu-trigger');trigger.click();
  assert.equal(trigger.getAttribute('aria-expanded'),'false');trigger.click();
  assert.equal(trigger.getAttribute('aria-expanded'),'true');
  dom.window.close();
});
test('shared field markers do not reorder checkboxes, and dynamic errors are announced',async()=>{
  const source=python("import web_portal_ui; print(web_portal_ui.PORTAL_JS[web_portal_ui.PORTAL_JS.index('/* Required/optional labels shared'):])");
  const dom=new JSDOM('<label>Retain password<input name="retained" type="checkbox" required></label><label>Description<input></label><p id="result" class="portal-status">Ready</p>',{runScripts:'outside-only',pretendToBeVisual:true});
  dom.window.eval(source);
  const doc=dom.window.document,label=doc.querySelector('label');
  assert.equal(label.firstElementChild.tagName,'INPUT');assert.equal(label.querySelectorAll('.field-requirement').length,1);
  assert.equal(doc.querySelectorAll('label')[1].querySelector('.field-requirement'),null);
  const result=doc.getElementById('result');result.className='portal-status error';result.textContent='Request failed';
  await new Promise(resolve=>dom.window.setTimeout(resolve,50));
  assert.equal(result.getAttribute('role'),'alert');
  result.className='portal-status success';await new Promise(resolve=>dom.window.setTimeout(resolve,50));
  assert.equal(result.getAttribute('role'),'status');dom.window.close();
});
test('update activity filters by words and status, escapes details, and has coloured outcome dots',()=>{
  const html=python(`from portal_activity_views import render_update_activity_page
print(render_update_activity_page('csrf', {'update_history': [
{'time':300,'event':'startup_failed','version':'alpha.105','detail':'<script>unsafe</script>'},
{'time':200,'event':'confirmed','version':'alpha.104','kind':'universal'},
{'time':100,'event':'unconfirmed','version':'alpha.103'}]}))`);
  const dom=new JSDOM(html,{runScripts:'outside-only'}),doc=dom.window.document;
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  const rows=[...doc.querySelectorAll('[data-activity-tone]')];
  assert.deepEqual(rows.map(row=>row.dataset.activityTone),['bad','good','warn']);
  assert.equal(rows.every(row=>row.querySelector('.history-marker').className==='history-marker'),true);
  assert.equal(doc.querySelector('.history-copy script'),null);
  const search=doc.getElementById('activity-search');search.value='ALPHA.104 universal';search.dispatchEvent(new dom.window.Event('input'));
  assert.deepEqual(rows.map(row=>row.hidden),[true,false,true]);
  const tone=doc.getElementById('activity-tone');tone.value='bad';tone.dispatchEvent(new dom.window.Event('change'));
  assert.equal(doc.getElementById('activity-empty').hidden,false);
  search.value='';search.dispatchEvent(new dom.window.Event('input'));assert.deepEqual(rows.map(row=>row.hidden),[false,true,true]);
  dom.window.close();
});
test('information activity dots stay small and do not inherit notification padding',()=>{
  const html=python(`from portal_activity_views import render_update_activity_page
print(render_update_activity_page('csrf', {'update_history': [{'time':300,'event':'confirmation_phase'}]}))`);
  const dom=new JSDOM(html),marker=dom.window.document.querySelector('.history-marker');
  const stylesheet=dom.window.document.createElement('style');
  stylesheet.textContent=python('import web_portal_ui; print(web_portal_ui.PORTAL_CSS)');
  dom.window.document.head.append(stylesheet);
  assert.equal(marker.dataset.tone,'info');
  assert.equal(marker.classList.contains('info'),false);
  const style=dom.window.getComputedStyle(marker);
  assert.equal(style.width,'10px');assert.equal(style.height,'10px');
  assert.equal(['','0','0px'].includes(style.padding),true);
  dom.window.close();
});
test('staged application, core and universal updates share a primary install button outside the milestone rail',()=>{
  for(const status of [
    {update_status:'ready',update_version:'3.0.0-alpha.105'},
    {firmware_update_supported:true,firmware_update_status:'ready',firmware_update_version:'3.0.0-alpha.105'},
    {universal_update_status:'ready',universal_update_version:'3.0.0-alpha.105',firmware_update_supported:true,firmware_update_status:'ready',update_status:'ready'}
  ]){
    const html=python(`import json; from portal_live_views import render_update_install_page; print(render_update_install_page('csrf',json.loads(${JSON.stringify(JSON.stringify(status))})))`);
    const dom=new JSDOM(html),doc=dom.window.document,steps=[...doc.querySelectorAll('.upgrade-stage-list li')];
    assert.equal(steps.length>2,true);assert.equal(steps.every(step=>step.querySelector('.upgrade-stage-ring')),true);
    assert.equal(doc.querySelector('.upgrade-stage-list form[action^="/activate-"]'),null);
    assert.equal(doc.querySelectorAll('#update-primary').length,1);
    assert.equal(doc.querySelector('#update-primary').closest('.upgrade-operation')!==null,true);
    const ring=steps.at(-1).querySelector('.upgrade-stage-ring');
    assert.equal(ring.getAttribute('role'),'img');
    assert.equal(ring.getAttribute('aria-label'),'Restart and install: Ready');
    assert.equal(ring.hasAttribute('aria-valuenow'),false);assert.equal(ring.textContent,'');
    assert.deepEqual([...doc.querySelectorAll('.manual-upgrade-buttons button')].map(button=>button.textContent),['Discard','Restart and install']);
    dom.window.close();
  }
});

test('certificate pages share a bounded responsive width and single-column certificate cards',()=>{
  for(const route of ['/certificates','/certificate-authorities','/api-client-trust','/device-certificates']){
    const html=python(`import web_portal; print(web_portal.render_certificate_route(${JSON.stringify(route)},'csrf',certificates={}))`);
    const dom=new JSDOM(html),doc=dom.window.document;
    const stylesheet=doc.createElement('style');stylesheet.textContent=python('import web_portal_ui; print(web_portal_ui.PORTAL_CSS)');doc.head.append(stylesheet);
    const workspace=doc.getElementById('certificate-workspace'),style=dom.window.getComputedStyle(workspace);
    assert.equal(style.width,'100%');assert.equal(style.maxWidth,'720px');
    assert.equal(workspace.querySelector('.module-grid'),null);
    for(const grid of workspace.querySelectorAll('.certificate-grid')){
      assert.equal(dom.window.getComputedStyle(grid).gridTemplateColumns,'minmax(0,1fr)');
    }
    dom.window.close();
  }
});

test('manual file selection keeps restart percentage-free and Discard before the primary action',()=>{
  const html=python("from portal_live_views import render_update_install_page; print(render_update_install_page('csrf',{},source='manual'))");
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://device.local'}),doc=dom.window.document;
  dom.window.eval(python('from portal_live_views import update_upload_script; print(update_upload_script())'));
  for(const extension of ['iotapp','iotcore','iotuni']){
    const input=doc.getElementById('update-bundle');Object.defineProperty(input,'files',{configurable:true,value:[new dom.window.File(['signed'],`test.${extension}`)]});
    input.dispatchEvent(new dom.window.Event('change'));
    const steps=[...doc.querySelectorAll('#update-stage-list li')],ring=steps.at(-1).querySelector('.upgrade-stage-ring');
    assert.equal(ring.getAttribute('role'),'img');assert.equal(ring.textContent,'');assert.equal(ring.hasAttribute('aria-valuenow'),false);
    assert.equal(steps[2].querySelector('[role=progressbar]').textContent,'0%');
    dom.window.eval('setMilestone(document.querySelector("#update-stage-list li:last-child"),"active",75)');
    assert.equal(ring.textContent,'');assert.equal(ring.getAttribute('aria-label'),'Restart and install: Ready');
    dom.window.eval('setMilestone(document.querySelector("#update-stage-list li:last-child"),"complete",100)');assert.equal(ring.textContent,'✓');
    assert.deepEqual([...doc.querySelectorAll('.manual-upgrade-buttons button')].map(button=>button.textContent),['Discard','Start update']);
  }
  dom.window.close();
});

test('automatic release selection and polling keep restart percentage-free and button order stable',async()=>{
  const status={release_checks_enabled:true,release_available_type:'universal',release_available_version:'3.0.0-alpha.110'};
  const html=python(`import json; from portal_live_views import render_update_install_page; print(render_update_install_page('csrf',json.loads(${JSON.stringify(JSON.stringify(status))}),source='automatic'))`);
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://device.local'}),doc=dom.window.document;
  dom.window.eval(python('from portal_live_views import automatic_upgrade_selection_script; print(automatic_upgrade_selection_script())'));
  const select=doc.getElementById('automatic-release-version-select');
  for(const kind of ['application','firmware','universal']){
    select.options[0].dataset.kind=kind;select.dispatchEvent(new dom.window.Event('change'));
    const ring=doc.querySelector('#automatic-stage-list li:last-child .upgrade-stage-ring');
    assert.equal(ring.getAttribute('role'),'img');assert.equal(ring.textContent,'');assert.equal(ring.hasAttribute('aria-valuenow'),false);
  }
  assert.deepEqual([...doc.querySelectorAll('.upgrade-operation .manual-upgrade-buttons button')].map(button=>button.textContent),['Discard','Start update']);
  const responses=[{task_id:'job'},{phase:'complete',percent:100}];
  dom.window.fetch=async()=>({ok:true,status:200,text:async()=>JSON.stringify(responses.shift()),json:async()=>responses.shift()});
  let refreshed=false;dom.window.portalRefreshTarget=()=>{refreshed=true;};
  dom.window.eval(python('from portal_live_views import automatic_upgrade_download_script; print(automatic_upgrade_download_script())'));
  doc.getElementById('automatic-download-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
  await new Promise(resolve=>dom.window.setTimeout(resolve,30));
  assert.equal(refreshed,true);
  const ring=doc.querySelector('#automatic-stage-list li:last-child .upgrade-stage-ring');
  assert.equal(ring.textContent,'');assert.equal(ring.getAttribute('aria-label'),'Restart and install: Ready');
  dom.window.close();
});

test('reconnected update tasks retain status-only restart circles through polling',async()=>{
  const html=python("from portal_live_views import render_upgrade_task_page; print(render_upgrade_task_page('csrf','job','Updating',{'release_available_type':'universal'}))");
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://device.local'}),doc=dom.window.document;
  dom.window.fetch=async()=>({ok:true,status:200,json:async()=>({phase:'writing',message:'Writing core firmware',percent:42})});
  for(const script of doc.querySelectorAll('script:not([src])'))dom.window.eval(script.textContent);
  await new Promise(resolve=>dom.window.setTimeout(resolve,30));
  const steps=[...doc.querySelectorAll('#upgrade-task-steps li')],ring=steps.at(-1).querySelector('.upgrade-stage-ring');
  assert.equal(ring.getAttribute('role'),'img');assert.equal(ring.textContent,'');assert.equal(ring.hasAttribute('aria-valuenow'),false);
  assert.equal(steps[4].querySelector('.upgrade-stage-ring').textContent,'42%');
  dom.window.setStep(steps.at(-1),'active',80);
  assert.equal(ring.textContent,'');assert.equal(ring.getAttribute('aria-label'),'Restart and install: Ready');
  const controls=doc.querySelector('.manual-upgrade-buttons');
  assert.equal(controls.firstElementChild.action,'https://device.local/discard-update');
  dom.window.close();
});
