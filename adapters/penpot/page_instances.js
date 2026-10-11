// Read true copy/master relationships and complete exports, preserving partial failures.
async function capturePenpotPageInstances(api,payload,execution,previous=null){
  if(api.currentFile?.id!==payload.fileReference||api.currentPage?.id!==execution.pageReference||execution.status!=='EXECUTED')throw new Error('page_instances_context_mismatch');
  const revision=api.currentFile.revn,rows=[],specs=[];
  if(previous&&(previous.fileReference!==payload.fileReference||previous.pageReference!==execution.pageReference||previous.rootReference!==execution.rootReference||previous.fileRevision!==revision||previous.createdNodeIds.length||previous.mutatedNodeIds.length))throw new Error('page_instances_previous_context_mismatch');
  function walk(spec){if(spec.componentReference)specs.push(spec);for(const child of spec.children||[])walk(child);}walk(payload.page);
  function observe(root){const nodes=[];function visit(n){nodes.push({reference:n.id,parentReference:n.parent?.id,type:n.type,name:n.name,x:n.x,y:n.y,width:n.width,height:n.height,fills:n.fills,strokes:n.strokes,opacity:n.opacity,rotation:n.rotation,flipX:n.flipX,flipY:n.flipY,hidden:n.hidden,visible:n.visible,blendMode:n.blendMode,shadows:n.shadows,blur:n.blur,borderRadius:n.borderRadius,clipContent:n.clipContent,d:n.d,commands:n.commands,characters:n.characters,fontId:n.fontId,fontFamily:n.fontFamily,fontVariantId:n.fontVariantId,fontWeight:n.fontWeight,fontStyle:n.fontStyle,fontSize:n.fontSize,lineHeight:n.lineHeight,letterSpacing:n.letterSpacing});for(const child of n.children||[])visit(child);}visit(root);return nodes;}
  const encode=bytes=>{let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);};
  for(const spec of specs){
    const instance=api.currentPage.getShapeById(execution.nodeMap[spec.id]),component=api.library.local.components.find(c=>c.id===spec.componentReference),main=component?.mainInstance();
    let ancestor=instance;while(ancestor&&ancestor.id!==execution.rootReference)ancestor=ancestor.parent;
    if(!ancestor||!instance?.isComponentCopyInstance()||!instance.isComponentRoot()||instance.component()?.id!==spec.componentReference||!main?.isComponentMainInstance()||!main.isComponentRoot())throw new Error('page_instances_identity_mismatch');
    const before=JSON.stringify({instance:observe(instance),main:observe(main)});let png,svg,issues=[];
    const prior=previous?.instances.find(r=>r.uiIrId===spec.id);
    if(prior&&(prior.componentReference!==component.id||prior.instanceReference!==instance.id||prior.mainReference!==main.id||JSON.stringify({instance:prior.instanceNodes,main:prior.mainNodes})!==before))throw new Error('page_instances_previous_geometry_mismatch');
    const reusedFormats=[];
    if(prior?.nativePngBase64){png=prior.nativePngBase64;reusedFormats.push('png');}else try{png=encode(await instance.export({type:'png',scale:1}));}catch(error){issues.push({format:'png',detail:String(error)});}
    if(prior?.nativeSvgBase64){svg=prior.nativeSvgBase64;reusedFormats.push('svg');}else try{svg=encode(await instance.export({type:'svg'}));}catch(error){issues.push({format:'svg',detail:String(error)});}
    const after={instance:observe(instance),main:observe(main)};
    if(JSON.stringify(after)!==before)throw new Error('page_instances_changed_during_capture');
    rows.push({uiIrId:spec.id,componentReference:component.id,mainReference:main.id,instanceReference:instance.id,isComponentCopy:true,isComponentRoot:true,isRealMain:true,instanceNodes:after.instance,mainNodes:after.main,nativePngBase64:png,nativeSvgBase64:svg,reusedFormats,exportIssues:issues,status:png&&svg?'CAPTURED':'PARTIAL'});
  }
  if(api.currentFile.revn!==revision||api.currentFile.id!==payload.fileReference||api.currentPage.id!==execution.pageReference)throw new Error('page_instances_document_changed');
  return {status:rows.every(r=>r.status==='CAPTURED')?'CAPTURED':'PARTIAL',platform:'penpot',scope:'production-native-instance-capture',fileReference:payload.fileReference,pageReference:execution.pageReference,rootReference:execution.rootReference,fileRevision:revision,createdNodeIds:[],mutatedNodeIds:[],instances:rows,reusedNativeFormats:!!previous,finalAcceptance:'NOT_RUN'};
}
