import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const {JSDOM}=require(process.env.IOT_UI_NODE_MODULES ? `${process.env.IOT_UI_NODE_MODULES}/jsdom` : 'jsdom');
const root=fileURLToPath(new URL('../..',import.meta.url));
const python=code=>execFileSync(process.env.PYTHON || 'python3',['-c',code],{cwd:root,encoding:'utf8'});
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
    assert.equal(steps.at(-1).querySelector('[role=progressbar]').getAttribute('aria-valuenow'),'0');
    dom.window.close();
  }
});
