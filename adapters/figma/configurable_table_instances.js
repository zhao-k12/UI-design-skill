// Actual linked instances; retry reads existing ledger rather than duplicates.
async function createConfigurableTableInstances(api){
  const result={scope:'task019_figma_linked_instances',status:'FAIL',fileReference:api.fileKey,createdNodeIds:[],mutatedNodeIds:[],instances:[],issues:[]};
  try{
    if(api.fileKey!=='0vGWSRoLxBiVPXiZ8xJAX9'||api.editorType!=='figma')throw Error('instance_file_mismatch');
    const page=await api.getNodeByIdAsync('69:2');await api.setCurrentPageAsync(page);
    const roots=[];
    for(const id of ['69:4','69:18']){
      const main=await api.getNodeByIdAsync(id);if(main?.type!=='COMPONENT'||main.parent.id!==page.id)throw Error('instance_main_missing');
      if(page.children.some(n=>n.name==='TASK-019 linked instance/'+id))throw Error('existing_instance_requires_read');
      for(const text of main.findAllWithCriteria({types:['TEXT']}))for(const segment of text.getStyledTextSegments(['fontName']))await api.loadFontAsync(segment.fontName);
      roots.push(main);
    }
    for(const main of roots){
      const instance=main.createInstance();page.appendChild(instance);instance.name='TASK-019 linked instance/'+main.id;instance.x=main.x;instance.y=400;
      const ids=[instance.id,...instance.findAll(()=>true).map(n=>n.id)];result.createdNodeIds.push(...ids);
      result.instances.push({instanceReference:instance.id,mainReference:(await instance.getMainComponentAsync()).id,nodeIds:ids,width:instance.width,height:instance.height});
    }
    result.status='CREATED';result.pageReference=page.id;
  }catch(error){result.issues.push({code:String(error.message)});}
  return result;
}
