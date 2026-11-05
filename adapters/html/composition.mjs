import { createApp, h, ref, nextTick } from 'vue';
import * as Official from 'view-ui-plus';

const ir=JSON.parse(document.getElementById('design-ir').textContent);
if(ir.schemaVersion!=='html-composition-v1')throw Error('unsupported_ui_ir');
const stage=ref('skeleton');
const columnFits=ref({});
const equalColumnWidths=ref({});
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
  if(layout.paddingX!==undefined){style.paddingLeft=`${spacing[layout.paddingX]}px`;style.paddingRight=`${spacing[layout.paddingX]}px`;}
  if(layout.paddingY!==undefined){style.paddingTop=`${spacing[layout.paddingY]}px`;style.paddingBottom=`${spacing[layout.paddingY]}px`;}
  if(layout.fill)style.flex='1 1 0%';
  if(layout.minHeight==='viewport')style.minHeight='100vh';
  if(layout.span)style.flex=`0 1 ${layout.span/24*100}%`;
  return style;
}
function render(node,scope={}){
  if(node.kind==='repeat')return bound(node.items,scope).map((item,index)=>render(node.template,{...scope,item,index}));
  if(node.kind==='text')return stage.value==='component'?String(node.defaultValue??'文本'):String(bound(node.value,scope));
  if(node.kind==='icon')return h(Official.Icon,{custom:iconClass(bound(node.name,scope))});
  if(node.kind==='asset'){
    const src=node.name==='project-logo'?node.dataUri:window.__designAssets?.[node.name];
    if(!src)throw Error(`missing_design_asset:${node.name}`);
    return h('img',{'data-tree-node':node.id,'data-component':'asset','data-asset-name':node.name,src,alt:node.alt||'默认 Logo',style:node.name==='default-avatar'?{height:'24px',width:'24px',objectFit:'cover',borderRadius:'50%',display:'block'}:{height:'32px',width:'auto',display:'block'}});
  }
  const attrs={'data-tree-node':node.id,'data-component':node.component||node.kind,...(node.designRole?{'data-design-role':node.designRole}:{})};
  if(node.allowLabelWrap===true)attrs['data-allow-label-wrap']='true';
  if(node.designRole==='uploaded-value'){
    const previewState=bound(node.previewState??'default',scope);
    if(!['default','hover'].includes(previewState))throw Error('invalid_preview_state');
    attrs['data-preview-state']=previewState;
    if(node.hoverPreview===true)attrs['data-hover-preview']='true';
  }
  if(node.kind==='container')return h(node.semantic==='navigation'?'nav':'div',{
    ...attrs,...(node.ariaLabel?{'aria-label':node.ariaLabel}:{}),style:layoutStyle(node.layout)
  },(node.children||[]).map(n=>render(n,scope)));
  const component=Official[node.component];
  if(!component)throw Error(`official_export_missing:${node.component}`);
  const rawProps={...(node.props||{})};
  if(node.component==='Table')delete rawProps.columns;
  let props=bound(rawProps,scope);
  if(node.current===true)attrs['aria-current']='page';
  if(stage.value==='component')props={...props,...bound(node.defaultProps||{},scope)};
  if(node.icon)props.customIcon=iconClass(bound(node.icon,scope));
  if(node.tabLabel)props.label=()=>render(node.tabLabel,scope);
  if(node.component==='Table'){
    // Column structure, cells, tree data and actions are configuration, never page-name branches.
    props.columns=(node.props?.columns||[]).map(col=>{
      const {cell,fitContent,...plain}=col;
      const fit=columnFits.value[node.id]?.[plain.key??plain.type];
      const equal=equalColumnWidths.value[node.id]?.[plain.key??plain.type];
      return {...bound(plain,scope),...(equal?{width:equal}:fit?(plain.width?{width:Math.max(plain.width,fit)}:{minWidth:Math.max(plain.minWidth||0,fit)}):{}),...(stage.value==='component'?{title:'列标题'}:{}),
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
window.__prepareLayout=async()=>{
  await window.__setStage('delivery');
  const fits={};const equalWidths={};const report=[];
  const canvas=document.createElement('canvas'),context=canvas.getContext('2d');
  for(const table of document.querySelectorAll('[data-component="Table"]')){
    const id=table.dataset.treeNode;
    const headers=[...table.querySelectorAll('.ivu-table-header thead tr:first-child th')];
    const body=[...table.querySelectorAll('.ivu-table-body tbody tr')];
    const entry={id,columns:[]};
    // Obtain declared column metadata without adding business-page branches.
    const find=node=>{
      if(node.id===id)return node;
      for(const child of [...(node.children||[]),...Object.values(node.slots||{}).flat(),...(node.template?[node.template]:[])]){const value=find(child);if(value)return value;}
    };
    const node=find(ir.root);if(!node||node.props?.columns?.some(col=>col.children))continue;
    const groups=body.map(row=>row.lastElementChild?.querySelector('[data-design-role="row-actions"]'));
    const singleAction=groups.length>0&&groups.every(group=>group&&group.children.length<=1)&&groups.some(group=>group.children.length===1);
    if(singleAction)entry.singleAction=true;
    (node.props.columns||[]).forEach((col,index)=>{
      if(col.fitContent===false)return;
      const cell=headers[index]?.querySelector('.ivu-table-cell');if(!cell)return;
      const style=getComputedStyle(cell);context.font=style.font;
      let needed=Math.max(context.measureText(String(col.title||'')).width,context.measureText('列标题').width);
      if(col.type==='selection')needed=cell.querySelector('.ivu-checkbox')?.getBoundingClientRect().width||needed;
      for(const row of body){
        const dataCell=row.children[index]?.querySelector('.ivu-table-cell');if(!dataCell)continue;
        const buttons=[...dataCell.querySelectorAll('button')];
        const avatar=dataCell.querySelector('.ivu-avatar');
        const actions=dataCell.querySelector('[data-design-role="row-actions"],[data-design-role="row-actions-left"]');
        if(actions){
          const children=[...actions.children],gap=parseFloat(getComputedStyle(actions).gap)||0;
          needed=Math.max(needed,children.reduce((n,b)=>n+b.getBoundingClientRect().width,0)+gap*Math.max(0,children.length-1));
        }else if(buttons.length){
          const gap=parseFloat(getComputedStyle(buttons[0].parentElement).gap)||0;
          needed=Math.max(needed,buttons.reduce((n,b)=>n+b.getBoundingClientRect().width,0)+gap*Math.max(0,buttons.length-1));
        }else if(avatar)needed=Math.max(needed,avatar.getBoundingClientRect().width);
        else if(!col.ellipsis){context.font=getComputedStyle(dataCell).font;needed=Math.max(needed,context.measureText(dataCell.innerText.trim()).width);}
      }
      needed=Math.ceil(needed+parseFloat(style.paddingLeft)+parseFloat(style.paddingRight)+(col.cell?.designRole==='row-actions-left'?0:2)+(singleAction&&index===node.props.columns.length-1?14:0));
      const key=col.key??col.type;(fits[id]??={})[key]=Math.max(fits[id][key]||0,needed);
      entry.columns.push({key,measuredMinimum:needed,declaredWidth:col.width??col.minWidth??null});
    });
    if(node.equalGapColumns && entry.columns.length===node.props.columns.length){
      const minimum=entry.columns.reduce((sum,col)=>sum+col.measuredMinimum,0);
      const available=Math.max(minimum,table.getBoundingClientRect().width-2);
      const spare=(available-minimum)/entry.columns.length;
      equalWidths[id]=Object.fromEntries(entry.columns.map(col=>[col.key,col.measuredMinimum+spare]));
      entry.equalGap={available,minimum,extraPerColumn:spare};
    }
    report.push(entry);
  }
  columnFits.value=fits;equalColumnWidths.value=equalWidths;await nextTick();
  // Persist content minima as CSS tracks. Static delivery must remain responsive
  // without a resize script or the pixel widths frozen by the official table.
  let css='';
  for(const entry of report){
    const table=document.querySelector(`[data-tree-node="${CSS.escape(entry.id)}"]`);
    if(!table?.closest('[data-design-role="table-panel"]'))continue;
    const actionGroups=[...table.querySelectorAll('.ivu-table-body tr td:last-child [data-design-role="row-actions"],.ivu-table-body tr td:last-child [data-design-role="row-actions-left"]')];
    const actionWidth=Math.max(0,...actionGroups.map(actions=>{const children=[...actions.children];return children.reduce((n,e)=>n+e.getBoundingClientRect().width,0)+Math.max(0,children.length-1)*(parseFloat(getComputedStyle(actions).gap)||0)}));
    const q=`[data-tree-node="${CSS.escape(entry.id)}"]`;
    if(entry.singleAction)css+=`${q} .ivu-table-body td:last-child .ivu-table-cell,${q} .ivu-table-header th:last-child .ivu-table-cell{padding-right:32px}${q} .ivu-table-header th:last-child .ivu-table-cell{display:flex;justify-content:flex-end}${q} .ivu-table-header th:last-child .ivu-table-cell>span:first-child{width:${actionWidth}px;flex:none;text-align:center}`;
    if(!entry.equalGap)continue;
    table.setAttribute('data-shared-table-scroll','true');
    const mins=entry.columns.map(c=>c.measuredMinimum), sum=mins.reduce((a,b)=>a+b,0);
    const fixedLast=actionGroups.length>0&&mins.length>1;
    const tracks=mins.map((n,i)=>fixedLast&&i===mins.length-1?`${n}px`:`calc((100% - ${sum}px) / ${mins.length-(fixedLast?1:0)} + ${n}px)`).join(' ');
    css+=`${q} .ivu-table{overflow-x:auto}${q} .ivu-table-header,${q} .ivu-table-body{overflow:visible!important;min-width:${sum}px}${q} .ivu-table-header table,${q} .ivu-table-body table,${q} thead,${q} tbody{display:block!important;width:100%!important;min-width:${sum}px}${q} colgroup{display:none}${q} .ivu-table-header tr,${q} .ivu-table-body tr{display:grid;width:100%;grid-template-columns:${tracks}}${q} .ivu-table-header th,${q} .ivu-table-body td{min-width:0}${q} .ivu-table-body td{display:flex;align-items:center}${q} .ivu-table-body td>.ivu-table-cell{width:100%}${q} .ivu-table:before,${q} .ivu-table:after{display:none!important}`;
    if(fixedLast)css+=`${q} .ivu-table-header th:last-child .ivu-table-cell{display:flex;justify-content:${entry.singleAction?'flex-end':'flex-start'}}${q} .ivu-table-header th:last-child .ivu-table-cell>span:first-child{width:${actionWidth}px;flex:none;text-align:center}`;
  }
  let dynamic=document.querySelector('style[data-responsive-tables]');if(!dynamic){dynamic=document.createElement('style');dynamic.dataset.responsiveTables='';document.head.append(dynamic)}dynamic.textContent=css;
  window.__sizingReport=report;
};
await nextTick();window.__ready=true;
