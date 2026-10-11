// Public SDK only: real component instances and independent stable native reads.
function tableInstanceNodes(root){
  const nodes=[];
  function visit(n){
    const entry={reference:n.id,parentReference:n.parent?.id,type:n.type,name:n.name,x:n.x,y:n.y,width:n.width,height:n.height,
      fills:n.fills,strokes:n.strokes,opacity:n.opacity,blendMode:n.blendMode,borderRadius:n.borderRadius,clipContent:n.clipContent,
      rotation:n.rotation,hidden:n.hidden,visible:n.visible,flipX:n.flipX,flipY:n.flipY,shadows:n.shadows,blur:n.blur};
    if(n.type==='text')Object.assign(entry,{characters:n.characters,fontId:n.fontId,fontFamily:n.fontFamily,fontVariantId:n.fontVariantId,
      fontSize:n.fontSize,fontWeight:n.fontWeight,fontStyle:n.fontStyle,lineHeight:n.lineHeight,letterSpacing:n.letterSpacing,
      growType:n.growType,textBounds:n.textBounds,align:n.align,verticalAlign:n.verticalAlign,
      direction:n.direction,textTransform:n.textTransform,textDecoration:n.textDecoration});
    nodes.push(entry);for(const child of n.children||[])visit(child);
  }
  visit(root);return nodes;
}
async function createTableLinkedInstances(api,execution){
  const result={scope:'task020_penpot_linked_instances',status:'FAIL',fileReference:api.currentFile.id,pageReference:api.currentPage.id,createdNodeIds:[],mutatedNodeIds:[],instances:[],issues:[]};
  try{
    if(execution.fileReference!==api.currentFile.id||execution.pageReference!==api.currentPage.id)throw Error('instance_context_mismatch');
    const components=[];
    for(const c of execution.candidates){
      const component=api.library.local.components.find(n=>n.id===c.componentReference),main=component?.mainInstance();
      if(!main?.isComponentMainInstance()||main.id!==c.mainReference)throw Error('instance_source_missing');
      if(api.currentPage.findShapes({name:'TASK-020 linked instance/'+c.componentReference}).length)throw Error('existing_instance_requires_read');
      components.push({component,main,logicalId:c.logicalId});
    }
    const instanceY=Math.max(...components.map(c=>c.main.y+c.main.height))+128;
    for(const {component,main,logicalId} of components){
      const instance=component.instance();result.createdNodeIds.push(...tableInstanceNodes(instance).map(n=>n.reference));
      instance.name='TASK-020 linked instance/'+component.id;instance.x=main.x;instance.y=instanceY;
      if(!instance.isComponentCopyInstance()||instance.component()?.id!==component.id)throw Error('instance_link_failed');
      result.instances.push({logicalId,componentReference:component.id,mainReference:main.id,instanceReference:instance.id});
    }
    await api.waitForLayoutUpdate();result.status='CREATED';
  }catch(error){result.issues.push({code:String(error.message)});}
  return result;
}
async function readTableLinkedInstance(api,execution,index){
  if(execution?.status!=='CREATED'||execution.fileReference!==api.currentFile.id||execution.pageReference!==api.currentPage.id)throw Error('instance_execution_required');
  const entry=execution.instances[index],instance=api.currentPage.getShapeById(entry.instanceReference),component=api.library.local.components.find(c=>c.id===entry.componentReference),main=component?.mainInstance();
  if(!instance?.isComponentCopyInstance()||instance.component()?.id!==component.id||main?.id!==entry.mainReference)throw Error('instance_link_mismatch');
  const revision=api.currentFile.revn,before={main:tableInstanceNodes(main),instance:tableInstanceNodes(instance)};
  const encode=bytes=>{let value='';for(let i=0;i<bytes.length;i+=8192)value+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(value);};
  const mainPng=await main.export({type:'png',scale:1}),instancePng=await instance.export({type:'png',scale:1});
  const after={main:tableInstanceNodes(main),instance:tableInstanceNodes(instance)};
  if(JSON.stringify(before)!==JSON.stringify(after)||api.currentFile.revn!==revision)throw Error('instance_document_changed');
  return{scope:'task020_penpot_instance_readback',status:'CAPTURED',fileReference:api.currentFile.id,pageReference:api.currentPage.id,fileRevision:revision,...entry,createdNodeIds:[],mutatedNodeIds:[],mainNodes:after.main,instanceNodes:after.instance,mainPngBase64:encode(mainPng),instancePngBase64:encode(instancePng)};
}
