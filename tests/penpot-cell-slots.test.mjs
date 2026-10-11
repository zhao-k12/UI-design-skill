import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync('adapters/penpot/section_patch.js','utf8')+'\n'+fs.readFileSync('adapters/penpot/cell_slots.js','utf8');
function fixture() {
  const nodes = new Map(); let calls = 0;
  function shape(id,type,width,height,parent=null) {
    const n = {id,type,name:id,width,height,x:0,y:0,parent,children:[],layoutChild:{},
      isComponentCopyInstance:()=>false,isComponentMainInstance:()=>false,
      resize(w,h){this.width=w;this.height=h;},appendChild(child){child.parent=this;this.children.push(child);}};
    nodes.set(id,n); return n;
  }
  const pageRoot=shape('page-root','root',100,100),root=shape('root','board',100,32,pageRoot),role=shape('role','board',28,32,root);
  root.children.push(role);pageRoot.children.push(root);
  const variant={fontVariantId:'regular',fontWeight:'400',fontStyle:'normal'};
  const font={fontFamily:'PingFang SC',variants:[variant],applyToText(n){n.fontFamily=this.fontFamily;}};
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:pageRoot,getShapeById:id=>nodes.get(id)},
    fonts:{findById:id=>id==='font'?font:null},library:{local:{components:[]}},
    createText(text){calls++;const n=shape('text-'+calls,'text',28,22);n.characters=text;return n;},waitForLayoutUpdate:async()=>{}};
  const context=vm.createContext({});vm.runInContext(code,context);
  const execution={status:'EXECUTED',fileReference:'file',pageReference:'page',rootReference:'root',createdNodeIds:['root','role'],nodeMap:{label:'role'}};
  const before={status:'CAPTURED',fileReference:'file',pageReference:'page',rootReference:'root',nodes:context.snapshotPenpotPatchRoot(root)};
  const request={items:[{roleId:'label',width:28,height:32,children:[{id:'label-text',type:'Text',name:'label-text',text:'姓名',
    fontBinding:{fontId:'font',fontVariantId:'regular',family:'PingFang SC',weight:400,style:'normal'},
    layout:{width:{mode:'fixed',value:28},height:{mode:'fixed',value:22}},
    style:{typographyToken:{fontSize:14,lineHeight:22,letterSpacing:0},colorToken:'#515a6e'}}]}]};
  return {context,api,execution,before,request,root,role,calls:()=>calls};
}
test('fills existing role while preserving page, Cell, source text and exact created ledger',async()=>{
  const f=fixture(),result=await f.context.fillPenpotCellSlots(f.api,f.execution,f.request,f.before);
  assert.equal(result.status,'FILLED');assert.equal(f.root.children[0],f.role);
  assert.equal(f.role.children[0].characters,'姓名');assert.equal(f.calls(),1);
  assert.deepEqual(Array.from(result.createdNodeIds),['text-1']);
  assert.equal(result.fullTask015Acceptance,false);
});
test('foreign, stale, duplicate or occupied role and missing font abort before writes',async()=>{
  for(const change of [f=>f.api.currentFile.id='foreign',f=>f.role.width=29,
    f=>f.request.items.push(f.request.items[0]),f=>f.role.children.push({id:'occupied'}),
    f=>f.request.items[0].children[0].fontBinding.fontId='missing']){
    const f=fixture();change(f);
    await assert.rejects(f.context.fillPenpotCellSlots(f.api,f.execution,f.request,f.before));
    assert.equal(f.calls(),0);
  }
});
