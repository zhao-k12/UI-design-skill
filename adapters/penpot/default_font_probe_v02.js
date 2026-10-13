function encodeDefaultFontPng(bytes) {
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';let text='';
  for(let i=0;i<bytes.length;i+=3) {const a=bytes[i],b=bytes[i+1],c=bytes[i+2];
    text+=alphabet[a>>2]+alphabet[((a&3)<<4)|((b??0)>>4)]+(b===undefined?'=':alphabet[((b&15)<<2)|((c??0)>>6)])+(c===undefined?'=':alphabet[c&63]);}
  return text;
}
async function observePenpotDefaultFont(penpot, expectedFile, expectedPage) {
  const record={scope:'platform-default-font-observation',version:'0.2.0',platform:'penpot',fileReference:expectedFile,
    pageReference:expectedPage,status:'FAIL',createdNodeIds:[],mutatedNodeIds:[],removedNodeIds:[],
    nativeAcceptance:'NOT_RUN',releaseReady:false,variants:[],samples:[],issues:[]};
  if(penpot.currentFile?.id!==expectedFile||penpot.currentPage?.id!==expectedPage) throw new Error('default_font_foreign_context');
  const before=penpot.currentPage.root.children.map(n=>n.id);let node;
  try {
    node=penpot.createText('User 0123456789');
    if(!node) throw new Error('default_font_text_creation_failed');
    record.createdNodeIds.push(node.id);
    record.defaultFont={family:node.fontFamily,fontId:node.fontId,fontVariantId:node.fontVariantId,weight:Number(node.fontWeight),style:node.fontStyle};
    const font=penpot.fonts.findById(node.fontId);
    if(!font||font.fontFamily!==node.fontFamily) throw new Error('default_font_not_available');
    record.variants=font.variants.map(v=>({family:font.fontFamily,fontId:font.fontId,fontVariantId:v.fontVariantId,
      weight:Number(v.fontWeight),style:v.fontStyle,name:v.name}));
    node.name='TASK-024 temporary native default font probe';
    node.x=Math.max(0,...penpot.currentPage.root.children.filter(n=>n.id!==node.id).map(n=>n.x+n.width))+160;node.y=0;
    node.growType='auto-width';
    for(const config of [{role:'body',weight:400,size:14},{role:'heading',weight:600,size:20}]) {
      const choices=font.variants.filter(v=>Number(v.fontWeight)===config.weight&&v.fontStyle==='normal');
      if(choices.length!==1) throw new Error('default_font_weight_missing_or_ambiguous:'+config.weight);
      font.applyToText(node,choices[0]);node.fontSize=String(config.size);
      node.characters='用户管理 姓名 状态 角色 查询 启用\nUser 0123456789';
      await new Promise(resolve=>setTimeout(resolve,150));
      const bytes=await node.export({type:'png',scale:2});
      if(node.textBounds.width<=0||node.textBounds.height<=0) throw new Error('default_font_sample_invalid');
      record.samples.push({role:config.role,fontSize:config.size,weight:Number(node.fontWeight),
        binding:{family:node.fontFamily,fontId:node.fontId,fontVariantId:node.fontVariantId,weight:Number(node.fontWeight),style:node.fontStyle},
        text:node.characters,width:node.width,height:node.height,textBounds:node.textBounds,nativePngBase64:encodeDefaultFontPng(bytes)});
    }
    record.status='PASS';
  } catch(error) {record.issues.push({code:'default_font_probe_failed',detail:String(error)});}
  finally {
    if(node) {const id=node.id;node.remove();record.removedNodeIds.push(id);}
    record.cleanupVerified=JSON.stringify(before)===JSON.stringify(penpot.currentPage.root.children.map(n=>n.id));
    if(!record.cleanupVerified) {record.status='FAIL';record.issues.push({code:'default_font_inventory_changed'});}
  }
  return record;
}
