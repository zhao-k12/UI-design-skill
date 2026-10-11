// Native static row/cell structure from the locked official Table fixture.
async function buildPenpotTableCandidate(api,spec) {
  if(api.currentFile?.id!==spec.fileReference||api.currentPage?.id!==spec.pageReference||spec.logicalId!=='data.table.default')throw new Error('candidate_context_mismatch');
  const exists=name=>typeof name==='string'&&name.includes(spec.logicalId)&&name.replace(/\s*\/\s*/g,'/').endsWith('/penpot-v1');
  if(api.currentPage.root.children.some(n=>exists(n.name))||api.library.local.components.some(c=>exists(c.mainInstance()?.name)))throw new Error('candidate_requires_recovery');
  const fonts=api.fonts.all.filter(f=>f.fontFamily===spec.fontFamily);if(fonts.length!==1)throw new Error('candidate_exact_font_missing_or_ambiguous');
  const font=fonts[0],variant=selectExactPenpotVariant(font,spec.fontWeight),created=[],textReferences=[];let component;
  const record=n=>{created.push(n.id);return n;};
  try {
    const root=record(api.createBoard());api.currentPage.root.appendChild(root);root.name=spec.name;
    root.resize(spec.rootBounds.width,spec.rootBounds.height);root.x=80;root.y=320;root.clipContent=true;root.opacity=1;root.fills=[];root.strokes=[];root.borderRadius=0;
    const board=(parent,bounds,name,fill)=>{
      const n=record(api.createBoard());parent.appendChild(n);n.name=name;n.resize(bounds.width,bounds.height);
      n.x=root.x+bounds.x;n.y=root.y+bounds.y;n.clipContent=false;n.opacity=1;n.borderRadius=0;n.strokes=[];n.fills=fill?[{fillColor:fill,fillOpacity:1}]:[];return n;
    };
    const rectangle=(parent,bounds,name,fill)=>{
      const n=record(api.createRectangle());parent.appendChild(n);n.name=name;n.resize(bounds.width,bounds.height);
      n.x=root.x+bounds.x;n.y=root.y+bounds.y;n.borderRadius=0;n.opacity=1;n.strokes=[];n.fills=[{fillColor:fill,fillOpacity:1}];n.setParentIndex(parent.children.length-1);return n;
    };
    for(const row of spec.rows){
      const rowNode=board(root,row.bounds,'official-source/'+row.path,null);
      for(const cell of row.cells){
        const cellNode=board(rowNode,cell.bounds,'official-source/'+cell.path,cell.fill),item=cell.text;
        const text=api.createText(item.characters);if(!text)throw new Error('candidate_text_creation_failed');record(text);textReferences.push(text.id);
        font.applyToText(text,variant);text.fontSize=String(item.fontSize);text.lineHeight=String(item.sourceTextBounds.height/item.fontSize);
        text.letterSpacing='0';text.growType='fixed';text.verticalAlign='top';text.align='left';text.opacity=1;text.strokes=[];
        text.fills=[{fillColor:item.fill,fillOpacity:1}];cellNode.appendChild(text);text.resize(item.sourceTextBounds.width,item.sourceTextBounds.height);
        text.x=root.x+item.sourceTextBounds.x;text.y=root.y+item.sourceTextBounds.y;text.name='official-source/'+item.path;
        if(text.fontFamily!==spec.fontFamily||Number(text.fontWeight)!==400)throw new Error('candidate_font_readback_mismatch');
      }
      rectangle(rowNode,{x:row.bounds.x,y:row.bounds.y+row.bounds.height-row.bottomBorder.height,width:row.bounds.width,height:row.bottomBorder.height},'official-source/row-border/'+row.path,row.bottomBorder.fill);
    }
    rectangle(root,{x:0,y:root.height-spec.bottomPseudo.height,width:spec.bottomPseudo.width,height:spec.bottomPseudo.height},'official-source/0.0::before',spec.bottomPseudo.fill);
    component=api.library.local.createComponent([root]);component.name='penpot-v1';component.path='candidate/'+spec.logicalId;
    await api.waitForLayoutUpdate();const main=component.mainInstance();if(!created.includes(main.id))created.push(main.id);
    return {status:'CANDIDATE_CREATED',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,
      componentReference:component.id,mainReference:main.id,textReference:textReferences[0],textReferences,logicalId:spec.logicalId,
      componentIrSha256:spec.componentIrSha256,createdNodeIds:created,mutatedNodeIds:[],admissionEligible:false,baselineCalibration:'NOT_RUN',fidelityGate:'NOT_RUN'};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,componentReference:component?.id,
    createdNodeIds:created,mutatedNodeIds:[],issues:[{code:'candidate_write_failed',detail:String(error)}],admissionEligible:false};}
}
