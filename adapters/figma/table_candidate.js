async function buildTableCandidate(api,request){
  const result={scope:'figma_table_candidate_build',status:'FAIL',logicalId:request.logicalId,createdNodeIds:[],mutatedNodeIds:[],createdStyleIds:[],issues:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
  try{
    if(api.fileKey!==request.fileReference||api.editorType!=='figma')throw new Error('table_file_mismatch');
    const page=await api.getNodeByIdAsync(request.pageReference);if(!page||page.type!=='PAGE')throw new Error('table_page_missing');await api.setCurrentPageAsync(page);
    if(page.children.some(n=>n.name==='candidate/'+request.logicalId))throw new Error('existing_table_candidate_requires_read');
    await api.loadFontAsync(request.fontName);
    const paints=css=>{const m=/^rgb\((\d+), (\d+), (\d+)\)$/.exec(css);if(!m)throw new Error('unsupported_table_css_paint');return[{type:'SOLID',color:{r:+m[1]/255,g:+m[2]/255,b:+m[3]/255}}];};
    const number=css=>{if(!/^\d+(?:\.\d+)?px$/.test(css))throw new Error('unsupported_table_css_length');return parseFloat(css);};
    const textStyles=await api.getLocalTextStylesAsync();let style=textStyles.find(s=>s.name==='Official/PingFang SC/Regular/14-21');
    if(!style){style=api.createTextStyle();result.createdStyleIds.push(style.id);style.name='Official/PingFang SC/Regular/14-21';style.fontName=request.fontName;style.fontSize=request.fontSize;style.lineHeight={unit:'PIXELS',value:request.lineHeight};}
    if(JSON.stringify(style.fontName)!==JSON.stringify(request.fontName)||style.fontSize!==request.fontSize||style.lineHeight.unit!=='PIXELS'||style.lineHeight.value!==request.lineHeight)throw new Error('incompatible_table_text_style');
    const root=api.createComponent();result.createdNodeIds.push(root.id);root.name='candidate/'+request.logicalId;root.description='Static official View UI Plus Table body. Exact source fixture; pending fidelity admission.';
    page.appendChild(root);root.x=Math.max(0,...page.children.filter(n=>n.id!==root.id).map(n=>n.x+n.width))+80;root.y=80;
    root.layoutMode='VERTICAL';root.primaryAxisSizingMode='FIXED';root.counterAxisSizingMode='FIXED';root.resize(request.rootBounds.width,request.rootBounds.height);root.fills=[];root.strokes=[];root.itemSpacing=0;root.clipsContent=true;
    for(const row of request.rows){
      const frame=api.createAutoLayout('HORIZONTAL');result.createdNodeIds.push(frame.id);frame.name='source/'+row.path;root.appendChild(frame);frame.resize(row.bounds.width,row.bounds.height);frame.layoutSizingHorizontal='FIXED';frame.layoutSizingVertical='FIXED';frame.fills=[];frame.strokes=[];frame.clipsContent=false;frame.itemSpacing=0;
      for(const cell of row.cells){
        const field=api.createAutoLayout('HORIZONTAL');result.createdNodeIds.push(field.id);field.name='source/'+cell.path;frame.appendChild(field);field.resize(cell.bounds.width,cell.bounds.height);field.layoutSizingHorizontal='FIXED';field.layoutSizingVertical='FIXED';field.fills=paints(cell.style['background-color']);field.clipsContent=false;field.strokes=paints(cell.style['border-bottom-color']);field.strokeAlign='INSIDE';field.strokeWeight=number(cell.style['border-bottom-width']);
        field.strokes=[]; // Same-paint adjacent bottom regions are one exact union.
        field.paddingTop=field.paddingRight=field.paddingBottom=field.paddingLeft=0;field.itemSpacing=0;
        const text=api.createText();result.createdNodeIds.push(text.id);field.appendChild(text);text.name='source/'+cell.text.path;text.layoutPositioning='ABSOLUTE';await text.setTextStyleIdAsync(style.id);text.characters=cell.text.characters;text.textAutoResize='NONE';text.resize(cell.text.width,request.lineHeight);text.x=cell.text.x;text.y=cell.text.y;text.fills=paints(cell.text.style['color']);
      }
      const border=api.createRectangle();result.createdNodeIds.push(border.id);frame.appendChild(border);border.name='source/row-border/'+row.path;border.layoutPositioning='ABSOLUTE';border.resize(row.bounds.width,row.bottomBorder.height);border.x=0;border.y=row.bounds.height-row.bottomBorder.height;border.fills=paints(row.bottomBorder.color);border.strokes=[];
    }
    const pseudo=api.createRectangle();result.createdNodeIds.push(pseudo.id);root.appendChild(pseudo);pseudo.name='source/0.0::before';pseudo.layoutPositioning='ABSOLUTE';pseudo.resize(request.bottomPseudo.width,request.bottomPseudo.height);pseudo.x=0;pseudo.y=request.rootBounds.height-request.bottomPseudo.height;pseudo.fills=paints(request.bottomPseudo.color);pseudo.strokes=[];
    result.status='PASS';result.componentReference=root.id;result.nativeObservation={componentReference:root.id,width:root.width,height:root.height,textReferences:root.findAllWithCriteria({types:['TEXT']}).map(n=>n.id)};
  }catch(error){result.issues.push({code:String(error.message)});}
  return result;
}
