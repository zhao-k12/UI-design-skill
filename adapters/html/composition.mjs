import { createApp, h, ref, nextTick } from 'vue';
import * as Official from 'view-ui-plus';

const ir=JSON.parse(document.getElementById('design-ir').textContent);
if(ir.schemaVersion!=='html-composition-v1')throw Error('unsupported_ui_ir');
const stage=ref('skeleton');
const spacing={none:0,xs:8,sm:12,md:16,lg:24};
function bound(value,scope){
  if(Array.isArray(value))return value.map(v=>bound(v,scope));
  if(value&&typeof value==='object'){
    if(Object.keys(value).length===1&&typeof value.bind==='string'){
      let result=scope;
      for(const part of value.bind.split('.')){
        if(['__proto__','prototype','constructor'].includes(part))throw Error('invalid_binding');
        result=result?.[part];
      }
      if(result===undefined)throw Error(`binding_missing:${value.bind}`);
      return result;
    }
    return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,bound(v,scope)]));
  }
  return value;
}
const iconClass=name=>`remix-custom remix-${name}`;
function layoutStyle(layout={}){
  const style={display:'flex',flexDirection:layout.direction==='horizontal'?'row':'column',minWidth:0,
    gap:`${spacing[layout.gap||'none']}px`,padding:`${spacing[layout.padding||'none']}px`,
    flexWrap:layout.wrap?'wrap':'nowrap',justifyContent:({start:'flex-start',end:'flex-end',center:'center','space-between':'space-between'})[layout.justify||'start'],
    alignItems:({start:'flex-start',end:'flex-end',center:'center',stretch:'stretch'})[layout.align||'stretch']};
  if(layout.fill)style.flex='1 1 0%';
  if(layout.minHeight==='viewport')style.minHeight='100vh';
  if(layout.span)style.flex=`0 1 ${layout.span/24*100}%`;
  return style;
}
function render(node,scope={}){
  if(node.kind==='repeat')return bound(node.items,scope).map((item,index)=>render(node.template,{...scope,item,index}));
  if(node.kind==='text')return stage.value==='component'?String(node.defaultValue??'文本'):String(bound(node.value,scope));
  if(node.kind==='icon')return h(Official.Icon,{custom:iconClass(bound(node.name,scope))});
  const attrs={'data-tree-node':node.id,'data-component':node.component||node.kind};
  if(node.kind==='container')return h('div',{...attrs,style:layoutStyle(node.layout)},(node.children||[]).map(n=>render(n,scope)));
  const component=Official[node.component];
  if(!component)throw Error(`official_export_missing:${node.component}`);
  const rawProps={...(node.props||{})};
  if(node.component==='Table')delete rawProps.columns;
  let props=bound(rawProps,scope);
  if(stage.value==='component')props={...props,...bound(node.defaultProps||{},scope)};
  if(node.icon)props.customIcon=iconClass(bound(node.icon,scope));
  if(node.component==='Table'){
    // Column structure, cells, tree data and actions are configuration, never page-name branches.
    props.columns=(node.props?.columns||[]).map(col=>{
      const {cell,...plain}=col;
      return {...bound(plain,scope),...(stage.value==='component'?{title:'列标题'}:{}),
        ...(cell?{render:(_,params)=>render(cell,{...scope,...params})}:
          stage.value==='component'&&!col.type?{render:()=> '默认内容'}:{})};
    });
  }
  const children=node.children||[];
  const slots=Object.fromEntries(Object.entries(node.slots||{}).map(([name,nodes])=>[name,params=>nodes.map(n=>render(n,{...scope,...params}))]));
  if(children.length)slots.default=()=>children.map(n=>render(n,scope));
  return h(component,{...props,...attrs},slots);
}
createApp({render:()=>h('main',{'data-composition-root':'',class:stage.value==='skeleton'?'composition-skeleton':''},[render(ir.root)])}).mount('#app');
window.__setStage=async value=>{stage.value=value;await nextTick();await document.fonts.ready;};
await nextTick();window.__ready=true;
