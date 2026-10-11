async function reviseTableBorders(api,request){
  const result={scope:'figma_table_source_border_revision',status:'FAIL',createdNodeIds:[],mutatedNodeIds:[],issues:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
  try{
    if(api.fileKey!==request.fileReference)throw new Error('table_revision_file_mismatch');const page=await api.getNodeByIdAsync(request.pageReference);await api.setCurrentPageAsync(page);const root=await api.getNodeByIdAsync('28:3');
    if(root?.type!=='COMPONENT'||root.name!=='candidate/data.table.default'||root.parent?.id!==page.id||root.findAll(n=>n.name==='source/0.0::before').length)throw new Error('table_revision_state_mismatch');
    for(const text of root.findAllWithCriteria({types:['TEXT']}))for(const segment of text.getStyledTextSegments(['fontName']))await api.loadFontAsync(segment.fontName);
    const paints=css=>{const m=/^rgb\((\d+), (\d+), (\d+)\)$/.exec(css);if(!m)throw new Error('invalid_table_revision_paint');return[{type:'SOLID',color:{r:+m[1]/255,g:+m[2]/255,b:+m[3]/255}}];};
    for(const row of request.rows){
      const frame=root.findAll(n=>n.name==='source/'+row.path)[0];if(!frame||frame.width!==row.bounds.width||frame.height!==row.bounds.height)throw new Error('table_revision_row_mismatch');
      for(const cell of row.cells){const field=frame.children.find(n=>n.name==='source/'+cell.path);if(!field||field.width!==cell.bounds.width||field.height!==cell.bounds.height)throw new Error('table_revision_cell_mismatch');field.strokes=[];result.mutatedNodeIds.push(field.id);}
      const border=api.createRectangle();result.createdNodeIds.push(border.id);frame.appendChild(border);result.mutatedNodeIds.push(frame.id);border.name='source/row-border/'+row.path;border.layoutPositioning='ABSOLUTE';border.resize(row.bounds.width,row.bottomBorder.height);border.x=0;border.y=row.bounds.height-row.bottomBorder.height;border.fills=paints(row.bottomBorder.color);border.strokes=[];
    }
    const pseudo=api.createRectangle();result.createdNodeIds.push(pseudo.id);root.appendChild(pseudo);result.mutatedNodeIds.push(root.id);pseudo.name='source/0.0::before';pseudo.layoutPositioning='ABSOLUTE';pseudo.resize(request.bottomPseudo.width,request.bottomPseudo.height);pseudo.x=0;pseudo.y=request.rootBounds.height-request.bottomPseudo.height;pseudo.fills=paints(request.bottomPseudo.color);pseudo.strokes=[];result.status='PASS';
  }catch(error){result.issues.push({code:String(error.message)});}
  return result;
}
