// Scoped measured Button baseline repair. Source span geometry remains explicit.
async function reviseButtonBaseline(api,request) {
  const result={scope:'figma_button_baseline_revision',status:'FAIL',createdNodeIds:[],mutatedNodeIds:[],issues:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
  try {
    if(api.editorType!=='figma'||api.fileKey!==request.fileReference)throw new Error('baseline_revision_file_mismatch');
    const s=request.source;
    const evidenceNames=['official-runtime-baseline-evidence.json','native-text-outline-capture.json','font-file-identity.json'];
    if(!s||!request.evidenceHashes||Object.keys(request.evidenceHashes).length!==evidenceNames.length||evidenceNames.some(name=>!/^[0-9a-f]{64}$/.test(request.evidenceHashes[name]))||![s.baselineComponentY,s.nativeSvgBaseline,s.spanBounds.width,s.spanBounds.height].every(Number.isFinite))throw new Error('baseline_revision_evidence_missing');
    const page=await api.getNodeByIdAsync(request.pageReference);
    if(!page||page.type!=='PAGE')throw new Error('baseline_revision_page_missing');
    await api.setCurrentPageAsync(page);
    const root=await api.getNodeByIdAsync(request.componentReference),text=await api.getNodeByIdAsync(request.textReference);
    if(!root||root.type!=='COMPONENT'||root.parent?.id!==page.id||!text||text.type!=='TEXT'||text.parent?.id!==root.id||root.children.length!==1||root.children[0].id!==text.id)throw new Error('baseline_revision_inventory_changed');
    if(root.width!==s.rootBounds.width||root.height!==s.rootBounds.height||text.characters!==s.text||JSON.stringify(text.fontName)!==JSON.stringify(s.fontName)||text.fontWeight!==s.fontWeight||text.fontSize!==s.fontSize||text.lineHeight.unit!=='PIXELS'||text.lineHeight.value!==s.lineHeight||text.width!==s.spanBounds.width||text.height!==s.spanBounds.height||text.x!==s.spanBounds.x||text.y!==s.spanBounds.y)throw new Error('baseline_revision_native_properties_changed');
    for(const node of [root,text]) {const m=node.absoluteTransform;if(m[0][0]!==1||m[0][1]!==0||m[1][0]!==0||m[1][1]!==1)throw new Error('baseline_revision_transform_unsupported');}
    for(const segment of text.getStyledTextSegments(['fontName']))await api.loadFontAsync(segment.fontName);
    const offset=s.baselineComponentY-s.spanBounds.y-s.nativeSvgBaseline;
    if(offset===0||Math.abs(offset)>s.spanBounds.height)throw new Error('baseline_revision_invalid_offset');
    const slot=api.createAutoLayout('HORIZONTAL');result.createdNodeIds.push(slot.id);
    root.appendChild(slot);result.mutatedNodeIds.push(root.id);
    slot.name='source/0.0';slot.resize(s.spanBounds.width,s.spanBounds.height);
    slot.layoutSizingHorizontal='FIXED';slot.layoutSizingVertical='FIXED';
    slot.paddingTop=0;slot.paddingRight=0;slot.paddingBottom=0;slot.paddingLeft=0;
    slot.itemSpacing=0;slot.fills=[];slot.strokes=[];slot.effects=[];slot.clipsContent=false;
    slot.primaryAxisAlignItems='MIN';slot.counterAxisAlignItems='MIN';
    slot.appendChild(text);result.mutatedNodeIds.push(text.id);
    text.layoutPositioning='ABSOLUTE';text.x=0;text.y=offset;
    if(slot.x!==s.spanBounds.x||slot.y!==s.spanBounds.y||text.y!==offset)throw new Error('baseline_revision_geometry_readback_mismatch');
    result.nativeObservation={componentReference:root.id,spanReference:slot.id,textReference:text.id,
      spanBounds:{x:slot.x,y:slot.y,width:slot.width,height:slot.height},textOffsetY:text.y,
      baselineComponentY:slot.y+text.y+s.nativeSvgBaseline,method:'source DOM baseline aligned to verified native font-outline baseline'};
    result.status='PASS';
  } catch(error) {result.issues.push({code:String(error.message)});}
  return result;
}
