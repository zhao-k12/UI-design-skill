import test from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {access,readFile} from 'node:fs/promises';
import {measureLayoutRelations} from '../adapters/html/layout-relations.mjs';

test('declared minimum spacing detects a toolbar touching its table',async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  await page.setContent('<div data-tree-node="toolbar" style="height:32px"></div><div data-tree-node="table" style="height:40px"></div>');
  const rule={id:'toolbar-spacing',kind:'minimum-gap',first:'toolbar',second:'table',axis:'vertical',minimum:'xs'};
  const touching=await page.evaluate(measureLayoutRelations,[rule]);
  assert.equal(touching.status,'FAIL');
  assert.ok(touching.results[0].issues.includes('minimum_gap_not_met'));
  await page.locator('[data-tree-node="table"]').evaluate(n=>n.style.marginTop='8px');
  const spaced=await page.evaluate(measureLayoutRelations,[rule]);
  assert.equal(spaced.status,'PASS');
  assert.equal(spaced.results[0].measurement.gap,8);
 }finally{await browser.close();}
});

test('same browser measurement rejects broken surfaces, shared edges and overflowing Card toolbars',async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1200,height:800}});
  // Test-only geometry, not a product style or official token definition.
  const fixture=broken=>`<style>body{margin:0}.sidebar{position:absolute;top:60px;left:0;width:200px;height:${broken?300:700}px;background:white}.main{position:absolute;left:200px;top:60px;width:1000px;height:700px}.nav{position:absolute;top:0;left:${broken?130:200}px;width:800px;height:60px}.ivu-card{position:absolute;left:220px;top:100px;width:800px}.ivu-card-head{height:48px}.ivu-card-extra{position:absolute;top:${broken?22:8}px;right:16px}.ivu-btn{height:32px}</style><div class="sidebar" data-tree-node="sidebar"></div><div class="main" data-tree-node="main"></div><div class="nav" data-tree-node="nav"></div><div class="ivu-card" data-tree-node="card"><div class="ivu-card-head">标题</div><div class="ivu-card-extra"><button class="ivu-btn">操作</button></div></div>`;
  const rules=[{id:'surface',kind:'surface-cover',surface:'sidebar',extent:'main',axis:'vertical'},
   {id:'boundary',kind:'edge-align',first:'nav',second:'sidebar',firstEdge:'left',secondEdge:'right'}];
  await page.setContent(fixture(true));
  const broken=await page.evaluate(measureLayoutRelations,rules);
  assert.equal(broken.status,'FAIL');
  assert.ok(broken.results[0].issues.includes('background_does_not_cover_region'));
  assert.ok(broken.results[1].issues.includes('shared_boundary_misaligned'));
  assert.ok(broken.results[2].issues.includes('card_toolbar_crosses_header_boundary'));
  await page.setContent(fixture(false));assert.equal((await page.evaluate(measureLayoutRelations,rules)).status,'PASS');
  // A contained toolbar need not share the header center. An explicit rule
  // still rejects that same geometry when the selected combination requires it.
  await page.locator('.ivu-card-extra').evaluate(n=>n.style.top='4px');
  const contained=await page.evaluate(measureLayoutRelations,rules);
  assert.equal(contained.status,'PASS');
  assert.equal(contained.results.find(r=>r.kind==='card-toolbar').measurement.centerDelta,4);
  await page.locator('.ivu-card-head').evaluate(n=>n.dataset.treeNode='card-head');
  await page.locator('.ivu-card-extra').evaluate(n=>n.dataset.treeNode='card-extra');
  const explicit=await page.evaluate(measureLayoutRelations,[{id:'chosen-center',kind:'vertical-center',first:'card-extra',second:'card-head'}]);
  assert.equal(explicit.results[0].status,'FAIL');
  assert.ok(explicit.results[0].issues.includes('vertical_centers_misaligned'));
  await page.locator('.sidebar').evaluate(n=>n.style.background='transparent');
  assert.equal((await page.evaluate(measureLayoutRelations,rules)).results[0].status,'FAIL');
  const missing=await page.evaluate(measureLayoutRelations,[{id:'missing',kind:'vertical-center',first:'absent',second:'nav'}]);
  assert.equal(missing.status,'FAIL');
  await browser.close();
 }finally{if(browser.isConnected())await browser.close();}
});

test('read-only regression detects the reported issues in the prior delivery without changing it',async t=>{
 const prior=resolve('artifacts/task-152/order-list/page.html');
 try{await access(prior);}catch{t.skip('Optional local historical delivery is absent');return;}
 const before=await readFile(prior);
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1912,height:956}});
  await page.goto(pathToFileURL(prior).href);
  const report=await page.evaluate(measureLayoutRelations,[
   {id:'side-fill',kind:'surface-cover',surface:'sidebar',extent:'main',axis:'vertical'},
   {id:'nav-start',kind:'edge-align',first:'top-navigation',second:'sidebar-column',firstEdge:'left',secondEdge:'right'}
  ]);
  assert.equal(report.status,'FAIL');
  // Historical screenshots exposed a visual alignment concern. Keep its
  // measurement, without treating center differences alone as universal FAIL.
  const toolbars=report.results.filter(r=>r.kind==='card-toolbar');
  assert.equal(toolbars.length,2);
  assert.ok(toolbars.every(r=>r.measurement.centerDelta>1));
  assert.equal(report.results.find(r=>r.id==='side-fill').status,'FAIL');
  assert.equal(report.results.find(r=>r.id==='nav-start').status,'FAIL');
  assert.deepEqual(await readFile(prior),before);
 }finally{await browser.close();}
});
