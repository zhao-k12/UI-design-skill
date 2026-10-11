// Import literal official SVGs. Native capture is separate from creation.
async function buildPenpotIcons(api,payload){
  if(api.currentFile?.id!==payload.fileReference||api.currentPage?.id!==payload.pageReference)throw new Error('icon_context_mismatch');
  const normalize=n=>String(n).replace(/\s*\/\s*/g,'/');
  if(payload.icons.some(i=>api.currentPage.root.children.some(n=>normalize(n.name)==='candidate/'+i.iconId+'/penpot-v1')))throw new Error('icon_requires_recovery');
  const created=[],masters=[];
  try{
    for(const [index,icon] of payload.icons.entries()){
      const group=api.createShapeFromSvg(icon.svg);if(!group)throw new Error('official_svg_import_failed');
      function record(n){if(!created.includes(n.id))created.push(n.id);for(const child of n.children||[])record(child);}record(group);
      if(group.width!==24||group.height!==24)throw new Error('official_viewbox_mismatch');
      api.currentPage.root.appendChild(group);group.name='candidate/'+icon.iconId+'/penpot-v1';group.x=0;group.y=0;group.opacity=1;
      const component=api.library.local.createComponent([group]);component.name='penpot-v1';component.path='candidate/'+icon.iconId;
      const main=component.mainInstance();main.opacity=1;record(main);
      if(!main.isComponentMainInstance()||!main.isComponentRoot())throw new Error('icon_not_real_master');
      masters.push({iconId:icon.iconId,svgSha256:icon.svgSha256,componentReference:component.id,mainReference:main.id});
    }
    await api.waitForLayoutUpdate();return {status:'ICONS_CREATED',platform:'penpot',fileReference:payload.fileReference,pageReference:payload.pageReference,registrySha256:payload.registrySha256,sourceVersion:payload.sourceVersion,createdNodeIds:created,mutatedNodeIds:[],masters,admissionEligible:false};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:payload.fileReference,pageReference:payload.pageReference,createdNodeIds:created,mutatedNodeIds:[],masters,issues:[{code:'icon_write_failed',detail:String(error)}],admissionEligible:false};}
}

async function capturePenpotIcons(api,request,{contentRaster=false}={}){
  if(api.currentFile?.id!==request.fileReference||api.currentPage?.id!==request.pageReference)throw new Error('icon_capture_context_mismatch');
  const encode=bytes=>{let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);};
  const revision=api.currentFile.revn,icons=[];
  const observe=main=>{
    const nodes=[];function visit(n){nodes.push({reference:n.id,parentReference:n.parent?.id,type:n.type,name:n.name,x:n.x,y:n.y,width:n.width,height:n.height,
      fills:n.fills,strokes:n.strokes,opacity:n.opacity,blendMode:n.blendMode,rotation:n.rotation,hidden:n.hidden,visible:n.visible,flipX:n.flipX,flipY:n.flipY,shadows:n.shadows,blur:n.blur,clipContent:n.clipContent,borderRadius:n.borderRadius,d:n.d,commands:n.commands});for(const child of n.children||[])visit(child);}visit(main);return nodes;
  };
  for(const master of request.masters){
    const main=api.library.local.components.find(c=>c.id===master.componentReference)?.mainInstance();
    if(!main||main.id!==master.mainReference||!main.isComponentMainInstance()||!main.isComponentRoot()||main.width!==24||main.height!==24)throw new Error('icon_capture_identity_mismatch');
    let rasterShape=main;
    if(contentRaster){
      const child=main.children?.[0];
      if(main.children.length!==1||child.type!=='group'||child.width!==24||child.height!==24||child.x!==main.x||child.y!==main.y||main.fills.length||main.strokes.length||main.opacity!==1||main.rotation!==0||main.shadows.length||main.blur||main.hidden!==false||main.visible!==true||main.flipX!==false||main.flipY!==false||main.blendMode!=='normal')throw new Error('icon_content_raster_not_equivalent');
      rasterShape=child;
    }
    const before=JSON.stringify(observe(main));let svg,png,contentSvg,issues=[];
    try{svg=encode(await main.export({type:'svg'}));}catch(error){issues.push({format:'svg',detail:String(error)});}
    if(contentRaster)try{contentSvg=encode(await rasterShape.export({type:'svg'}));}catch(error){issues.push({format:'content-svg',detail:String(error)});}
    try{png=encode(await rasterShape.export({type:'png',scale:1}));}catch(error){issues.push({format:'png',detail:String(error)});}
    const nodes=observe(main);if(JSON.stringify(nodes)!==before)throw new Error('icon_changed_during_capture');
    icons.push({...master,nodes,nativeSvgBase64:svg,nativePngBase64:png,...(contentRaster?{rasterShapeReference:rasterShape.id,nativeRasterSvgBase64:contentSvg,rasterScope:'original-content-group-under-transparent-component-board'}:{}),exportIssues:issues,status:svg&&png&&(!contentRaster||contentSvg)?'CAPTURED':'PARTIAL'});
  }
  if(api.currentFile.revn!==revision||api.currentFile.id!==request.fileReference||api.currentPage.id!==request.pageReference)throw new Error('icon_document_changed');
  return {status:icons.every(i=>i.status==='CAPTURED')?'CAPTURED':'PARTIAL',platform:'penpot',scope:'production',evidenceKind:'native-platform-export',fileReference:request.fileReference,pageReference:request.pageReference,fileRevision:revision,registrySha256:request.registrySha256,sourceVersion:request.sourceVersion,createdNodeIds:[],mutatedNodeIds:[],icons,admissionEligible:false};
}

async function restorePenpotIconSourcePaths(api,request,payload){
  if(api.currentFile?.id!==payload.fileReference||api.currentPage?.id!==payload.pageReference||request.fileReference!==payload.fileReference||request.pageReference!==payload.pageReference)throw new Error('icon_restore_context_mismatch');
  const mutated=[];
  for(const master of request.masters){
    const source=payload.icons.find(i=>i.iconId===master.iconId&&i.svgSha256===master.svgSha256);
    const main=api.library.local.components.find(c=>c.id===master.componentReference)?.mainInstance();
    if(!source||!main||main.id!==master.mainReference||!main.isComponentMainInstance()||main.width!==24||main.height!==24)throw new Error('icon_restore_identity_mismatch');
    const paths=[];function walk(n){if(n.type==='path')paths.push(n);for(const child of n.children||[])walk(child);}walk(main);
    const matches=[...source.svg.matchAll(/<path d="([^"]+)"\s*\/>/g)];
    if(paths.length!==1||matches.length!==1)throw new Error('icon_restore_unsupported_inventory');
    main.x=0;main.y=0;main.opacity=1;mutated.push(main.id);
    if(main.children.length!==1||main.children[0].type!=='group')throw new Error('icon_restore_unsupported_wrapper');
    main.children[0].opacity=1;mutated.push(main.children[0].id);
    paths[0].d=matches[0][1];paths[0].fills=[{fillColor:'#000000',fillOpacity:1}];paths[0].strokes=[];mutated.push(paths[0].id);
  }
  await api.waitForLayoutUpdate();return {status:'SOURCE_PATHS_RESTORED',platform:'penpot',fileReference:payload.fileReference,pageReference:payload.pageReference,createdNodeIds:[],mutatedNodeIds:mutated,admissionEligible:false};
}
