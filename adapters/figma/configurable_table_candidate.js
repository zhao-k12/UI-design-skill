async function buildConfigurableFigmaTables(api,specs){
  const result={status:'FAIL',scope:'figma_configurable_table_build',createdNodeIds:[],mutatedNodeIds:[],createdStyleIds:[],candidates:[],issues:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
  const record=node=>{result.createdNodeIds.push(node.id);return node;};
  try{
    if(api.editorType!=='figma'||specs.length!==2||new Set(specs.map(s=>s.logicalId)).size!==2||specs.some(s=>s.fileReference!==api.fileKey||!/^data\.table\.config\.[a-f0-9]{64}$/.test(s.logicalId)))throw Error('table_context_mismatch');
    const pageName='TASK-019 official mixed-font table candidates';
    if(api.root.children.some(p=>p.name===pageName))throw Error('existing_table_page_requires_read');
    const available=await api.listAvailableFontsAsync();const styles=await api.getLocalTextStylesAsync();const styleMap=new Map();
    for(const family of ['Arial','PingFang SC']){
      const font={family,style:'Regular'};if(!available.some(f=>JSON.stringify(f.fontName)===JSON.stringify(font)))throw Error('missing_source_font:'+family);
      await api.loadFontAsync(font);
      const name='Official/'+family+'/Regular/14-21';const matches=styles.filter(s=>s.name===name);if(matches.length>1)throw Error('ambiguous_text_style');
      if(matches.length){const style=matches[0];if(JSON.stringify(style.fontName)!==JSON.stringify(font)||style.fontSize!==14||style.lineHeight.unit!=='PIXELS'||style.lineHeight.value!==21||style.letterSpacing.value!==0)throw Error('incompatible_table_text_style');styleMap.set(family,style);}
    }
    const page=record(api.createPage());page.name=pageName;await api.setCurrentPageAsync(page);result.fileReference=api.fileKey;result.pageReference=page.id;
    for(const family of ['Arial','PingFang SC'])if(!styleMap.has(family)){const style=api.createTextStyle();result.createdStyleIds.push(style.id);style.name='Official/'+family+'/Regular/14-21';style.fontName={family,style:'Regular'};style.fontSize=14;style.lineHeight={unit:'PIXELS',value:21};style.letterSpacing={unit:'PIXELS',value:0};styleMap.set(family,style);}
    const paint=hex=>{if(!/^#[a-f0-9]{6}$/i.test(hex))throw Error('unsupported_source_paint');return[{type:'SOLID',color:{r:parseInt(hex.slice(1,3),16)/255,g:parseInt(hex.slice(3,5),16)/255,b:parseInt(hex.slice(5,7),16)/255}}];};
    for(const spec of specs){
      const root=record(api.createComponent());page.appendChild(root);root.name=spec.name;root.description='Official source-bound Table body; pending Figma font encoding and full fidelity admission.';
      root.x=Math.max(0,...page.children.filter(n=>n.id!==root.id).map(n=>n.x+n.width))+80;root.y=80;root.layoutMode='VERTICAL';root.primaryAxisSizingMode='FIXED';root.counterAxisSizingMode='FIXED';root.resize(spec.rootBounds.width,spec.rootBounds.height);root.fills=paint(spec.rootFill);root.strokes=[];root.itemSpacing=0;root.paddingTop=root.paddingRight=root.paddingBottom=root.paddingLeft=0;root.clipsContent=true;
      const textReferences=[];
      for(const row of spec.rows){
        const frame=record(api.createAutoLayout('HORIZONTAL'));root.appendChild(frame);frame.name='source/'+row.path;frame.resize(row.bounds.width,row.bounds.height);frame.layoutSizingHorizontal='FIXED';frame.layoutSizingVertical='FIXED';frame.fills=[];frame.strokes=[];frame.clipsContent=false;frame.itemSpacing=0;frame.paddingTop=frame.paddingRight=frame.paddingBottom=frame.paddingLeft=0;
        for(const cell of row.cells){
          const field=record(api.createAutoLayout('HORIZONTAL'));frame.appendChild(field);field.name='source/'+cell.path;field.resize(cell.bounds.width,cell.bounds.height);field.layoutSizingHorizontal='FIXED';field.layoutSizingVertical='FIXED';field.fills=paint(cell.fill);field.strokes=[];field.clipsContent=false;field.itemSpacing=0;field.paddingTop=field.paddingRight=field.paddingBottom=field.paddingLeft=0;
          const item=cell.text,text=record(api.createText());field.appendChild(text);text.name='source/'+item.path;text.layoutPositioning='ABSOLUTE';await text.setTextStyleIdAsync(styleMap.get(item.fontFamily).id);text.characters=item.characters;text.textAutoResize='WIDTH_AND_HEIGHT';text.textTruncation='DISABLED';text.x=item.sourceTextBounds.x-cell.bounds.x;text.y=item.sourceBaselineY-cell.bounds.y-spec.fontBaselineOffsets[item.fontFamily];text.fills=paint(item.fill);textReferences.push(text.id);
        }
        const border=record(api.createRectangle());frame.appendChild(border);border.name='source/row-border/'+row.path;border.layoutPositioning='ABSOLUTE';border.resize(row.bounds.width,row.bottomBorder.height);border.x=0;border.y=row.bounds.height-row.bottomBorder.height;border.fills=paint(row.bottomBorder.fill);border.strokes=[];
      }
      const pseudo=record(api.createRectangle());root.appendChild(pseudo);pseudo.name='source/0.0::before';pseudo.layoutPositioning='ABSOLUTE';pseudo.resize(spec.bottomPseudo.width,spec.bottomPseudo.height);pseudo.x=0;pseudo.y=root.height-spec.bottomPseudo.height;pseudo.fills=paint(spec.bottomPseudo.fill);pseudo.strokes=[];
      result.candidates.push({logicalId:spec.logicalId,componentReference:root.id,pageReference:page.id,fileReference:api.fileKey,width:root.width,height:root.height,textReferences,componentIrSha256:spec.componentIrSha256,fontCalibrationCaptureHashes:spec.fontCalibrationCaptureHashes});
    }
    result.status='CANDIDATES_CREATED';
  }catch(error){result.issues.push({code:String(error.message)});}
  return result;
}
