// Runs inside the existing page/session. No writes, screenshot sampling or CSS repair.
export function measureLayoutRelations(relations = []) {
  const rect = element => {
    const r = element.getBoundingClientRect();
    return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};
  };
  const find = id => [...document.querySelectorAll('[data-tree-node]')].filter(n=>n.dataset.treeNode===id);
  const results = [];
  const emit = (id,kind,issues,measurement) => results.push({id,kind,status:issues.length?'FAIL':'PASS',issues,measurement});
  for (const rule of relations) {
    const keys = rule.kind==='surface-cover'?['surface','extent']:['first','second'];
    const matches = keys.map(key=>find(rule[key]));
    if(matches.some(nodes=>nodes.length!==1)){
      emit(rule.id,rule.kind,['relation_requires_unique_rendered_nodes'],{});continue;
    }
    const [a,b]=matches.map(nodes=>nodes[0]), ar=rect(a),br=rect(b),issues=[];
    if(!ar.width||!ar.height||!br.width||!br.height)issues.push('relation_node_not_visible');
    if(rule.kind==='surface-cover'){
      if((rule.axis!=='vertical'&&(ar.left>br.left+1||ar.right<br.right-1))||ar.top>br.top+1||ar.bottom<br.bottom-1)issues.push('background_does_not_cover_region');
      const s=getComputedStyle(a),color=s.backgroundColor;
      // A transparent wrapper is not proof of a continuous painted surface.
      const alpha=color==='transparent'?0:color.startsWith('rgba(')?Number(color.split(',').at(-1).replace(')','')):1;
      if(alpha<1&&s.backgroundImage==='none')issues.push('surface_owner_has_no_opaque_background');
      emit(rule.id,rule.kind,issues,{surface:ar,extent:br,backgroundColor:color,backgroundImage:s.backgroundImage});
    }else if(rule.kind==='edge-align'){
      const delta=Math.abs(ar[rule.firstEdge]-br[rule.secondEdge]);
      if(!Number.isFinite(delta)||delta>1)issues.push('shared_boundary_misaligned');
      emit(rule.id,rule.kind,issues,{first:ar,second:br,delta});
    }else if(rule.kind==='vertical-center'){
      const delta=Math.abs((ar.top+ar.bottom-br.top-br.bottom)/2);
      if(delta>1)issues.push('vertical_centers_misaligned');
      emit(rule.id,rule.kind,issues,{first:ar,second:br,delta});
    }else emit(rule.id,rule.kind,['unknown_layout_relation_kind'],{});
  }
  // Always inspect every actual Card extra toolbar, including multiple cards.
  for(const [index,card] of [...document.querySelectorAll('.ivu-card')].entries()){
    const head=[...card.children].find(n=>n.classList.contains('ivu-card-head'));
    const extra=[...card.children].find(n=>n.classList.contains('ivu-card-extra'));
    if(!head||!extra)continue;
    const controls=[...extra.querySelectorAll('.ivu-btn,.ivu-select,.ivu-input-wrapper')].filter(n=>{const r=n.getBoundingClientRect();return r.width&&r.height;});
    if(!controls.length)continue;
    const hr=rect(head),boxes=controls.map(rect);
    const bounds={top:Math.min(...boxes.map(r=>r.top)),bottom:Math.max(...boxes.map(r=>r.bottom)),left:Math.min(...boxes.map(r=>r.left)),right:Math.max(...boxes.map(r=>r.right))};
    const delta=Math.abs((bounds.top+bounds.bottom-hr.top-hr.bottom)/2),issues=[];
    if(delta>1)issues.push('card_toolbar_not_vertically_centered');
    if(bounds.top<hr.top||bounds.bottom>hr.bottom-1)issues.push('card_toolbar_crosses_header_boundary');
    if(bounds.left<hr.left||bounds.right>hr.right)issues.push('card_toolbar_exceeds_header_width');
    emit(`card-toolbar:${card.dataset.treeNode||'card'}:${index}`,'card-toolbar',issues,{header:hr,controls:bounds,centerDelta:delta});
  }
  return {status:results.some(r=>r.status==='FAIL')?'FAIL':'PASS',results,
    tolerance:'1 CSS px for rounding, not a design spacing token',
    scope:'Declared geometry and own surface paint plus all native Card extra toolbars; visual review still required.'};
}
