async function observeFigmaDefaultFont(figma, expectedFile, expectedPage) {
  const record = {scope:'platform-default-font-observation', version:'0.2.0', platform:'figma', fileReference:expectedFile,
    pageReference:expectedPage, status:'FAIL', createdNodeIds:[], mutatedNodeIds:[], removedNodeIds:[],
    nativeAcceptance:'NOT_RUN', releaseReady:false, variants:[], samples:[], issues:[]};
  if(figma.fileKey!==expectedFile) throw new Error('default_font_foreign_file');
  const page=await figma.getNodeByIdAsync(expectedPage);
  if(!page||page.type!=='PAGE') throw new Error('default_font_page_missing');
  await figma.setCurrentPageAsync(page);
  const before=page.children.map(n=>n.id); let node;
  try {
    const available=await figma.listAvailableFontsAsync();
    node=figma.createText(); record.createdNodeIds.push(node.id);
    const original=node.fontName;
    if(original===figma.mixed) throw new Error('default_font_mixed');
    record.defaultFont={family:original.family,style:original.style,weight:node.fontWeight};
    const fonts=available.filter(f=>f.fontName.family===original.family);
    if(!fonts.some(f=>f.fontName.style===original.style)) throw new Error('default_font_not_available');
    await figma.loadFontAsync(original);
    node.name='TASK-024 temporary native default font probe';
    node.x=Math.max(0,...page.children.filter(n=>n.id!==node.id).map(n=>n.x+n.width))+160; node.y=0;
    node.textAutoResize='WIDTH_AND_HEIGHT'; node.characters='User 0123456789';
    for(const font of fonts) {
      await figma.loadFontAsync(font.fontName); node.fontName=font.fontName;
      const segments=node.getStyledTextSegments(['fontName','fontWeight','fontStyle']);
      if(segments.length!==1) throw new Error('default_font_style_ambiguous');
      record.variants.push({family:original.family,style:font.fontName.style,weight:node.fontWeight,fontStyle:segments[0].fontStyle});
    }
    for(const config of [{role:'body',weight:400,size:14},{role:'heading',weight:600,size:20}]) {
      const choices=record.variants.filter(v=>v.weight===config.weight&&v.fontStyle!=='ITALIC');
      if(choices.length!==1) throw new Error('default_font_weight_missing_or_ambiguous:'+config.weight);
      const choice=choices[0];
      await figma.loadFontAsync({family:choice.family,style:choice.style});
      node.fontName={family:choice.family,style:choice.style}; node.fontSize=config.size;
      node.textAutoResize='HEIGHT'; node.resize(480,100);
      node.characters='用户管理 姓名 状态 角色 查询 启用\nUser 0123456789';
      await node.exportAsync({format:'PNG',constraint:{type:'SCALE',value:1}});
      const bytes=await node.exportAsync({format:'PNG',constraint:{type:'SCALE',value:1}});
      if(node.hasMissingFont||node.width<=0||node.height<=0) throw new Error('default_font_sample_invalid');
      record.samples.push({role:config.role,fontSize:config.size,weight:node.fontWeight,
        binding:{family:choice.family,style:choice.style},text:node.characters,width:node.width,height:node.height,
        layoutMode:'fixed-width-auto-height',layoutWidth:480,exportScale:1,
        nativePngBase64:figma.base64Encode(bytes)});
    }
    record.status='PASS';
  } catch(error) {record.issues.push({code:'default_font_probe_failed',detail:String(error)});}
  finally {
    if(node&&!node.removed) {const id=node.id;node.remove();record.removedNodeIds.push(id);}
    record.cleanupVerified=JSON.stringify(before)===JSON.stringify(page.children.map(n=>n.id));
    if(!record.cleanupVerified) {record.status='FAIL';record.issues.push({code:'default_font_inventory_changed'});}
  }
  return record;
}
