import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {chromium} from 'playwright';

test('summary and steps align within the shared page frame', async()=>{
  const css=await readFile(new URL('../adapters/html/confirmed-modules.css',import.meta.url),'utf8');
  const viewCss=await readFile(new URL('../node_modules/view-ui-plus/dist/styles/viewuiplus.css',import.meta.url),'utf8');
  const b=await chromium.launch();
  try{
    const p=await b.newPage({viewport:{width:1200,height:600}});
    await p.setContent(`<style>body{margin:0}*{box-sizing:border-box}${viewCss}${css}</style><div data-design-role="breadcrumb">位置</div><div data-design-role="table-panel"><div data-design-role="summary-header"><div data-design-role="summary-title">商机标题</div><i class="remix-custom"></i></div></div><div class="ivu-steps ivu-steps-horizontal" data-design-role="progress-steps"><div class="ivu-steps-item"><div class="ivu-steps-tail"><i></i></div><div class="ivu-steps-head"><div class="ivu-steps-head-inner">1</div></div><div class="ivu-steps-main"><div class="ivu-steps-title">步骤名称</div><div class="ivu-steps-content">时间</div></div></div><div class="ivu-steps-item"><div class="ivu-steps-head"><div class="ivu-steps-head-inner">2</div></div><div class="ivu-steps-main"><div class="ivu-steps-title">下一步</div></div></div></div>`);
    const r=await p.evaluate(()=>{const q=s=>document.querySelector(s),rect=s=>q(s).getBoundingClientRect(),center=x=>(x.top+x.bottom)/2;const panel=rect('[data-design-role=table-panel]'),close=rect('[data-design-role=summary-header]>.remix-custom'),head=rect('.ivu-steps-head-inner'),title=rect('.ivu-steps-title'),line=rect('.ivu-steps-tail i'),content=rect('.ivu-steps-content');return {margin:getComputedStyle(q('[data-design-role=table-panel]')).marginTop,closeTop:close.top-panel.top,titleDiff:Math.abs(center(head)-center(title)),lineDiff:Math.abs(center(head)-center(line)),contentDiff:Math.abs(content.left-title.left)}});
    assert.equal(r.margin,'0px');assert.equal(r.closeTop,16);assert.ok(r.titleDiff<1);assert.ok(r.lineDiff<=0.5);assert.ok(r.contentDiff<1);
  }finally{await b.close()}
});

test('form sections preserve spacing and fixed actions above scrollable content', async()=>{
  const css=await readFile(new URL('../adapters/html/confirmed-modules.css',import.meta.url),'utf8');
  const b=await chromium.launch();
  try{
    const p=await b.newPage({viewport:{width:1200,height:360}});
    await p.setContent(`<style>body{margin:0}*{box-sizing:border-box}${css}</style><div data-design-role="page-shell" style="display:flex"><aside data-design-role="sidebar"></aside><main data-tree-node="x-main" style="flex:1"><div data-design-role="form-section"><div data-design-role="form-section-title">标题</div><div data-design-role="form-grid"><div class="ivu-form-item" style="height:34px">一</div><div class="ivu-form-item" style="height:34px;grid-column:1">二</div></div></div><div data-design-role="page-actions"><button>返回</button><button>提交</button></div></main></div>`);
    const r=await p.evaluate(()=>{let section=document.querySelector('[data-design-role=form-section]').getBoundingClientRect(),title=document.querySelector('[data-design-role=form-section-title]').getBoundingClientRect(),fields=[...document.querySelectorAll('.ivu-form-item')].map(x=>x.getBoundingClientRect()),footer=document.querySelector('[data-design-role=page-actions]').getBoundingClientRect(),buttons=[...document.querySelectorAll('button')].map(x=>x.getBoundingClientRect());return {left:section.left-256,titleLeft:title.left-section.left,titleTop:title.top-section.top,titleGap:fields[0].top-title.bottom,rowGap:fields[1].top-fields[0].bottom,bottom:section.bottom-fields[1].bottom,height:footer.height,barBottom:innerHeight-footer.bottom,btnGap:buttons[1].left-buttons[0].right,right:innerWidth-buttons[1].right}});
    assert.deepEqual(r,{left:24,titleLeft:16,titleTop:16,titleGap:24,rowGap:24,bottom:16,height:56,barBottom:0,btnGap:12,right:24});
  }finally{await b.close()}
});

test('detail row actions and add button align with their table', async()=>{
  const css=await readFile(new URL('../adapters/html/confirmed-modules.css',import.meta.url),'utf8');
  const b=await chromium.launch();
  try{
    const p=await b.newPage({viewport:{width:1200,height:500}});
    await p.setContent(`<style>*{box-sizing:border-box}${css}table{width:100%;border-collapse:collapse}td{height:48px}button{height:32px}</style><div data-design-role="form-section" style="display:flex;flex-direction:column"><table><tbody><tr><td><div class="ivu-table-cell"><span data-design-role="detail-action"><i class="remix-custom"></i>删除</span></div></td></tr></tbody></table><button data-design-role="detail-add">新增</button></div>`);
    const r=await p.evaluate(()=>{const t=document.querySelector('table').getBoundingClientRect(),a=document.querySelector('[data-design-role=detail-add]').getBoundingClientRect(),td=document.querySelector('td').getBoundingClientRect(),item=document.querySelector('[data-design-role=detail-action]').getBoundingClientRect();return {gap:a.top-t.bottom,left:a.left-t.left,padding:getComputedStyle(document.querySelector('button')).padding,border:getComputedStyle(document.querySelector('button')).borderWidth,vertical:Math.abs((td.top+td.bottom-item.top-item.bottom)/2),horizontal:Math.abs((td.left+td.right-item.left-item.right)/2)}});
    assert.equal(r.gap,16);assert.equal(r.left,0);assert.equal(r.padding,'0px');assert.equal(r.border,'0px');assert.ok(r.vertical<1);assert.ok(r.horizontal<1);
  }finally{await b.close()}
});
