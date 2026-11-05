import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {pathToFileURL} from 'node:url';

const root=resolve(import.meta.dirname,'..');
const base=join(root,'artifacts','task-143','composition-smoke-'+Date.now());
const text=(id,value)=>({id,kind:'text',value,defaultValue:'默认文案'});
const component=(id,name,props={},children=[])=>({id,kind:'component',component:name,props,children});
function input(grouped){
  const actions={id:'actions',kind:'repeat',items:{bind:'row.actions'},template:{
    ...component('row-action','Button',{type:'text',size:'small'},[text('action-label',{bind:'item.label'})]),icon:{bind:'item.icon'}}};
  const cols=[{title:'名称',key:'name'},{title:'状态',key:'status',cell:component('status','Tag',{color:{bind:'row.color'}},[text('status-copy',{bind:'row.status'})])},
    {title:'操作',key:'actions',cell:{id:'action-layout',kind:'container',layout:{direction:'horizontal'},children:[actions]}}];
  if(grouped)cols.splice(1,0,{title:'人员',key:'owner'},{title:'备注',key:'note'});
  const row={name:'开发样例A',status:'启用',color:'green',owner:'示例人员',note:'示例备注',actions:grouped?[{label:'查看',icon:'eye-line'}]:[{label:'编辑',icon:'edit-line'},{label:'删除',icon:'delete-bin-line'}]};
  const table=component('records','Table',{columns:cols,data:grouped?[row]:[row,{...row,name:'开发样例B'}],stripe:true});
  const nav=component('nav','Menu',{theme:'dark',width:'auto',activeName:'a'},grouped?[{
    ...component('group','Submenu',{name:'g'},[component('child','MenuItem',{name:'a'},[text('child-label','子级')])]),
    slots:{title:[text('group-label','分组')]}}]:[
      {id:'nav-repeat',kind:'repeat',items:[{key:'a',label:'第一项'},{key:'b',label:'第二项'}],template:component('nav-item','MenuItem',{name:{bind:'item.key'}},[text('nav-label',{bind:'item.label'})])}]);
  const toolbar={id:'tools',kind:'container',layout:{direction:'horizontal',gap:'xs'},children:[
    {...component('create','Button',{type:'primary'},[text('create-label','新增')]),icon:'add-line'},
    {...component('search','Input',{search:true,placeholder:'来源搜索'}),defaultProps:{placeholder:'默认搜索'}}]};
  const detail=component('detail','Card',{},[component('form','Form',{},[
    component('field','FormItem',{label:'名称'},[component('value','Input',{modelValue:'开发样例'})])])]);
  const page=grouped?{id:'page',kind:'container',layout:{gap:'md',paddingX:'lg',paddingY:'xs'},children:[detail,nav,table,toolbar]}:
    component('page','Layout',{},[component('side','Sider',{},[nav]),component('content','Content',{},[
      {id:'body',kind:'container',layout:{padding:'lg',gap:'md'},children:[toolbar,table]}])]);
  page.sourceIds=['fixture'];
  return {title:'配置变体开发测试',icons:['add-line','eye-line','edit-line','delete-bin-line'],root:page};
}

test('same compiler and renderer handle different ordering, menus, columns, rows and bound actions',async()=>{
  await mkdir(base,{recursive:true});
  const source=join(base,'developer-fixture.txt');await writeFile(source,'Development fixture, not a user prototype');
  const sourceSha256=createHash('sha256').update(await readFile(source)).digest('hex');
  const traits={leading:'none',trailing:'none',surface:'plain',shape:'rect',role:'development-fixture'};
  const observation={sourceSha256,items:[{id:'fixture',region:'page',traits,decision:'include',sourceEvidence:'Developer fixture',treeRef:'root'}]};
  const scan={sourceSha256,items:[{id:'fixture',region:'page',traits,visual:'Independent development-fixture input'}]};
  const browser=await chromium.launch({headless:true});
  try{
    for(const grouped of [false,true]){
      const dir=join(base,grouped?'reordered-grouped':'flat');await mkdir(dir,{recursive:true});
      for(const [name,value] of Object.entries({'content-tree':{sourceSha256,...input(grouped)},observation,scan}))await writeFile(join(dir,name+'.json'),JSON.stringify(value));
      execFileSync(join(root,'.venv/Scripts/python.exe'),['-X','utf8','core/pipeline/html_composition.py','--source',source,'--content',join(dir,'content-tree.json'),'--observation',join(dir,'observation.json'),'--independent-scan',join(dir,'scan.json'),'--output-dir',join(dir,'core')],{cwd:root,stdio:'pipe'});
      execFileSync(process.execPath,['scripts/export_html_composition.mjs',join(dir,'core'),join(dir,'html')],{cwd:root,stdio:'pipe'});
      const qa=JSON.parse(await readFile(join(dir,'html/qa.json')));
      assert.equal(qa.status,'PASS');
      assert.deepEqual(qa.stages.delivery.tableColumnCounts,[grouped?5:3]);
      assert.equal(qa.stages.delivery.tableRows,grouped?1:2);
      assert.equal(qa.stages.delivery.arrows,grouped?1:0);
      assert.equal(qa.stages.delivery.menuItems,grouped?1:2);
      const page=await browser.newPage();await page.goto(pathToFileURL(join(dir,'html/page.html')).href);
      assert.equal(await page.locator('script').count(),0);
      assert.equal(await page.locator('[data-tree-node="row-action"]').count(),grouped?1:4);
      assert.equal(await page.locator('.ivu-tag-green').count(),grouped?1:2);
      assert.equal(await page.locator('.ivu-input').first().evaluate(n=>getComputedStyle(n).pointerEvents),'none');
      assert.equal((await page.locator('body').innerText()).includes('开发样例A'),true);
      assert.equal(qa.stages.component.texts.includes('开发样例A'),false);
      if(grouped){
        const order=await page.locator('[data-tree-node="page"] > [data-tree-node]').evaluateAll(nodes=>nodes.map(n=>n.dataset.treeNode));
        assert.deepEqual(order,['detail','nav','records','tools']);
        const padding=await page.locator('[data-tree-node="page"]').evaluate(n=>{const s=getComputedStyle(n);return [s.paddingTop,s.paddingRight,s.paddingBottom,s.paddingLeft]});
        assert.deepEqual(padding,['8px','24px','8px','24px']);
      }
      await page.close();
    }
  }finally{await browser.close();}
});

test('uploaded value preview state follows row data instead of row position',async()=>{
  const dir=join(base,'explicit-preview');await mkdir(dir,{recursive:true});
  const source=join(dir,'source.txt');await writeFile(source,'Developer fixture');
  const sourceSha256=createHash('sha256').update(await readFile(source)).digest('hex');
  const traits={leading:'none',trailing:'none',surface:'plain',shape:'rect',role:'fixture'};
  const observation={sourceSha256,items:[{id:'fixture',region:'page',traits,decision:'include',sourceEvidence:'Fixture',treeRef:'records'}]};
  const scan={sourceSha256,items:[{id:'fixture',region:'page',traits,visual:'Fixture'}]};
  const cell={id:'uploaded',kind:'container',designRole:'uploaded-value',previewState:{bind:'row.preview'},
    layout:{direction:'horizontal'},children:[text('amount',{bind:'row.amount'}),{id:'delete',kind:'icon',name:'delete-bin-line'}]};
  const content={sourceSha256,title:'fixture',root:{...component('records','Table',{columns:[{title:'值',key:'amount',cell}],data:[
    {amount:'A',preview:'default'},{amount:'B',preview:'hover'}]}),sourceIds:['fixture']}};
  for(const [name,value] of Object.entries({'content-tree':content,observation,scan}))await writeFile(join(dir,name+'.json'),JSON.stringify(value));
  execFileSync(join(root,'.venv/Scripts/python.exe'),['-X','utf8','core/pipeline/html_composition.py','--source',source,'--content',join(dir,'content-tree.json'),'--observation',join(dir,'observation.json'),'--independent-scan',join(dir,'scan.json'),'--output-dir',join(dir,'core')],{cwd:root,stdio:'pipe'});
  execFileSync(process.execPath,['scripts/export_html_composition.mjs',join(dir,'core'),join(dir,'html')],{cwd:root,stdio:'pipe'});
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage();await page.goto(pathToFileURL(join(dir,'html/page.html')).href);
    const values=page.locator('[data-design-role="uploaded-value"]');
    assert.deepEqual(await values.evaluateAll(es=>es.map(e=>({state:e.dataset.previewState,visible:getComputedStyle(e.querySelector('.remix-delete-bin-line')).visibility}))),
      [{state:'default',visible:'hidden'},{state:'hover',visible:'visible'}]);
  }finally{await browser.close()}
});
