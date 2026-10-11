async function restoreFigmaTableSizing(api,execution,specs){
  const result={status:'FAIL',createdNodeIds:[],mutatedNodeIds:[],observations:[],issues:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
  try{
    if(api.fileKey!==execution.fileReference||execution.status!=='CANDIDATES_CREATED'||execution.candidates.length!==specs.length)throw Error('table_sizing_execution_mismatch');
    const page=await api.getNodeByIdAsync(execution.pageReference);if(!page||page.type!=='PAGE')throw Error('table_page_missing');await api.setCurrentPageAsync(page);
    const selected=[];
    for(let i=0;i<specs.length;i++){
      const candidate=execution.candidates[i],spec=specs[i],root=await api.getNodeByIdAsync(candidate.componentReference);
      if(root?.type!=='COMPONENT'||root.parent.id!==page.id||candidate.logicalId!==spec.logicalId||root.width!==spec.rootBounds.width||root.height!==spec.rootBounds.height)throw Error('table_sizing_root_mismatch');
      const items=spec.rows.flatMap(r=>r.cells.map(c=>c.text));
      if(root.findAllWithCriteria({types:['TEXT']}).length!==items.length||candidate.textReferences.length!==items.length)throw Error('table_sizing_text_inventory_mismatch');
      for(let j=0;j<items.length;j++){
        const item=items[j],text=await api.getNodeByIdAsync(candidate.textReferences[j]);let parent=text;while(parent&&parent.id!==root.id)parent=parent.parent;
        if(!parent||text.type!=='TEXT'||text.name!=='source/'+item.path||text.characters!==item.characters||text.fontName.family!==item.fontFamily||text.fontName.style!=='Regular'||text.fontSize!==14||text.lineHeight.unit!=='PIXELS'||text.lineHeight.value!==21||text.letterSpacing.value!==0||text.textAutoResize!=='NONE'||text.width!==item.sourceTextBounds.width||text.height!==21)throw Error('table_sizing_text_requires_read');
        if(JSON.stringify(item.sourceSizing)!==JSON.stringify({display:'inline',width:'auto',height:'auto'}))throw Error('source_sizing_not_auto');
        selected.push({text,item});
      }
    }
    const fonts=new Map();for(const {text} of selected)for(const segment of text.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(segment.fontName),segment.fontName);
    for(const font of fonts.values())await api.loadFontAsync(font);
    for(const {text,item} of selected){const before={x:text.x,y:text.y,width:text.width,height:text.height,textAutoResize:text.textAutoResize};text.textAutoResize='WIDTH_AND_HEIGHT';result.mutatedNodeIds.push(text.id);result.observations.push({textReference:text.id,characters:text.characters,sourceSizing:item.sourceSizing,before,after:{x:text.x,y:text.y,width:text.width,height:text.height,textAutoResize:text.textAutoResize}});}
    result.fileReference=api.fileKey;result.pageReference=page.id;result.status='SOURCE_TEXT_SIZING_RESTORED';
  }catch(error){result.issues.push({code:String(error.message)});}
  return result;
}
