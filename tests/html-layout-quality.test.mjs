import test from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {measureLayoutQuality} from '../adapters/html/layout-quality.mjs';

test('measures clipped placeholders and wrapping labels, preserving explicit/top-label exceptions',async()=>{
 const browser=await chromium.launch();
 try {
  const page=await browser.newPage();
  await page.setContent(`<style>input{box-sizing:border-box;font:14px Arial;padding:7px;border:1px solid}
   .ivu-form-item-label{display:block;font:14px/20px Arial;width:35px}</style>
   <div data-tree-node="narrow"><input class="ivu-input" style="width:40px" placeholder="Complete placeholder"></div>
   <div data-tree-node="wide"><input class="ivu-input" style="width:250px" placeholder="Complete placeholder"></div>
   <div data-tree-node="select"><div class="ivu-select-selection"><span class="ivu-select-selected-value" style="display:block;width:20px;white-space:nowrap;overflow:hidden">Database query</span></div></div>
   <div class="ivu-form"><div data-tree-node="wrapped" data-component="FormItem"><label class="ivu-form-item-label">Long field label</label></div>
   <div data-tree-node="intentional" data-component="FormItem" data-allow-label-wrap="true"><label class="ivu-form-item-label">Long field label</label></div></div>
   <div class="ivu-form ivu-form-label-top"><label class="ivu-form-item-label">Long field label</label></div>`);
  const result=await page.evaluate(measureLayoutQuality);
  assert.equal(result.status,'FAIL');
  assert.deepEqual(result.results.filter(r=>r.status==='FAIL').map(r=>r.id),['narrow','wrapped','select']);
  assert.equal(result.results.find(r=>r.id==='wide').status,'PASS');
  await page.locator('[data-tree-node=narrow] input').evaluate(e=>e.style.width='250px');
  await page.locator('[data-tree-node=wrapped] label').evaluate(e=>e.style.width='250px');
  await page.locator('.ivu-select-selected-value').evaluate(e=>e.style.width='250px');
  assert.equal((await page.evaluate(measureLayoutQuality)).status,'PASS');
 } finally { await browser.close(); }
});

test('rejects missing module margins, duplicate metadata gap and misplaced close geometry',async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage();
  await page.setContent(`<div style="width:600px"><div data-tree-node="summary" data-design-role="summary-panel" style="position:relative">
   <div data-design-role="summary-heading" style="height:26px">Title</div>
   <div data-tree-node="close" data-design-role="module-close" style="position:absolute;top:0;right:0;width:10px;height:10px"></div>
   <div data-tree-node="meta" data-design-role="summary-meta" style="margin-top:32px">Metadata</div></div>
   <div data-tree-node="steps" data-design-role="steps-panel">Steps</div></div>`);
  const result=await page.evaluate(measureLayoutQuality);
  const issues=result.results.flatMap(r=>r.issues);
  for(const expected of ['module_outer_spacing_mismatch','module_gap_mismatch','summary_close_geometry_mismatch','summary_meta_gap_mismatch'])assert.ok(issues.includes(expected),expected);
 }finally{await browser.close();}
});

test('smaller viewport rejects page overflow even without form controls or module roles',async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage({viewport:{width:1428,height:808}});
  await page.setContent('<div style="width:1200px;height:100px">Fixed content</div>');
  assert.equal((await page.evaluate(measureLayoutQuality)).status,'PASS');
  await page.setViewportSize({width:1100,height:700});
  assert.ok((await page.evaluate(measureLayoutQuality)).results.some(r=>r.issues.includes('viewport_overflow')));
 }finally{await browser.close();}
});
