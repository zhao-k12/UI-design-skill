// The host supplies independently source-verified, approval-bound unions.
async function repairHeadedTableHeaders(api, specs, execution) {
  if(execution?.status!=='CREATED'||api.currentFile?.id!==execution.fileReference||api.currentPage?.id!==execution.pageReference)throw new Error('headed_repair_context_mismatch');
  const observations=[];
  for(let i=0;i<specs.length;i++){
    const spec=specs[i],candidate=execution.candidates[i],union=spec.headerBackgroundUnion;
    if(!union||candidate.logicalId!==spec.logicalId||candidate.componentIrSha256!==spec.componentIrSha256)throw new Error('headed_repair_source_mismatch');
    const main=api.currentPage.getShapeById(candidate.mainReference);
    if(!main?.isComponentMainInstance()||main.width!==spec.rootBounds.width||main.height!==spec.rootBounds.height||!main.clipContent)throw new Error('headed_repair_main_mismatch');
    const normalize=name=>name.replace(/\s*\/\s*/g,'/');
    const rows=main.children.filter(n=>normalize(n.name)==='official-source/'+union.rowPath);
    if(rows.length!==1)throw new Error('headed_repair_row_ambiguous');
    const row=rows[0],b=union.bounds;
    if(row.type!=='board'||row.x-main.x!==b.x||row.y-main.y!==b.y||row.width!==b.width||row.height!==b.height||row.opacity!==1||row.clipContent||row.strokes.length||row.borderRadius!==0)throw new Error('headed_repair_row_geometry_mismatch');
    const exactFill=n=>n.fills.length===1&&n.fills[0].fillColor===union.fill&&n.fills[0].fillOpacity===1&&!n.fills[0].fillColorGradient&&!n.fills[0].fillImage;
    if(row.fills.length&&!exactFill(row))throw new Error('headed_repair_existing_fill_mismatch');
    for(const cell of spec.rows[0].cells){
      const matches=row.children.filter(n=>normalize(n.name)==='official-source/'+cell.path);
      const n=matches[0],c=cell.bounds;
      if(matches.length!==1||n.type!=='board'||n.x-main.x!==c.x||n.y-main.y!==c.y||n.width!==c.width||n.height!==c.height||n.opacity!==1||!exactFill(n))throw new Error('headed_repair_cell_mismatch');
    }
    observations.push({logicalId:spec.logicalId,mainReference:main.id,rowReference:row.id,union,beforeFills:JSON.parse(JSON.stringify(row.fills))});
  }
  const mutated=[];
  for(const item of observations){const row=api.currentPage.getShapeById(item.rowReference);row.fills=[{fillColor:item.union.fill,fillOpacity:1}];mutated.push(row.id);}
  await api.waitForLayoutUpdate();
  for(const item of observations)item.afterFills=JSON.parse(JSON.stringify(api.currentPage.getShapeById(item.rowReference).fills));
  return {status:'HEADER_UNION_RESTORED',fileReference:execution.fileReference,pageReference:execution.pageReference,observations,createdNodeIds:[],mutatedNodeIds:mutated,fidelityGate:'NOT_RUN',admissionEligible:false};
}
