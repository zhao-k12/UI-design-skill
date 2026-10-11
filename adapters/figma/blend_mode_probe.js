// Reversible instrumentation of existing static candidates; never admission.
async function probeTextBlendMode(api,request) {
  const result={scope:'figma_text_blend_mode_experiment',status:'FAIL',fileReference:api.fileKey,
    pageReference:request.pageReference,componentReference:request.componentReference,logicalId:request.logicalId,
    createdNodeIds:[],mutatedNodeIds:[],restoredNodeIds:[],observations:{},rasters:{},issues:[],
    admissionEligible:false,fidelityGate:'NOT_RUN'};
  let root,texts=[],originals=[];
  const copy=value=>value===api.mixed?{nativeMixed:true}:JSON.parse(JSON.stringify(value));
  function snapshot() {
    const rows=[];
    function visit(node) {
      const row={reference:node.id,type:node.type,parentReference:node.parent?.id,
        absoluteTransform:copy(node.absoluteTransform),absoluteBounds:copy(node.absoluteBoundingBox),properties:{}};
      for(const key of ['name','visible','opacity','blendMode','fills','strokes','effects','isMask','rotation',
          'clipsContent','cornerRadius','strokeWeight','strokeAlign','layoutMode','itemSpacing',
          'paddingTop','paddingRight','paddingBottom','paddingLeft','layoutPositioning',
          'layoutSizingHorizontal','layoutSizingVertical','characters','fontName','fontWeight','fontSize',
          'lineHeight','letterSpacing','textCase','textDecoration','paragraphIndent','paragraphSpacing',
          'textAlignHorizontal','textAlignVertical','textAutoResize']) {
        if(key in node)row.properties[key]=copy(node[key]);
      }
      rows.push(row);if('children' in node)for(const child of node.children)visit(child);
    }
    visit(root);return rows;
  }
  async function raster(label) {
    const bytes=await root.exportAsync({format:'PNG',constraint:{type:'SCALE',value:1},useAbsoluteBounds:true});
    result.rasters[label]={format:'PNG',scale:1,encoding:'base64',data:api.base64Encode(bytes)};
  }
  try {
    if(api.editorType!=='figma'||api.fileKey!==request.fileReference)throw new Error('blend_probe_file_mismatch');
    if(!request.logicalId||!Array.isArray(request.textReferences)||!request.textReferences.length||new Set(request.textReferences).size!==request.textReferences.length)throw new Error('blend_probe_invalid_inventory');
    const page=await api.getNodeByIdAsync(request.pageReference);
    if(!page||page.type!=='PAGE')throw new Error('blend_probe_page_missing');
    await api.setCurrentPageAsync(page);
    root=await api.getNodeByIdAsync(request.componentReference);
    if(!root||root.type!=='COMPONENT'||root.parent?.id!==page.id)throw new Error('blend_probe_component_missing');
    texts=root.findAllWithCriteria({types:['TEXT']});
    if(texts.length!==request.textReferences.length||texts.some(node=>!request.textReferences.includes(node.id)))throw new Error('blend_probe_text_inventory_changed');
    if(texts.some(node=>node.blendMode!=='PASS_THROUGH'||node.opacity!==1||node.effects.length!==0||node.isMask!==false))throw new Error('blend_probe_text_state_unsupported');
    for(const text of texts)for(const segment of text.getStyledTextSegments(['fontName']))await api.loadFontAsync(segment.fontName);
    originals=texts.map(text=>text.blendMode);
    result.observations.before=snapshot();await raster('before');
    for(const text of texts) {result.mutatedNodeIds.push(text.id);text.blendMode='NORMAL';}
    result.observations.normal=snapshot();await raster('normal');
    result.status='PASS';
  } catch(error) {result.issues.push({code:String(error.message)});}
  finally {
    if(result.mutatedNodeIds.length) {
      for(const [index,text] of texts.entries()) {
        if(!result.mutatedNodeIds.includes(text.id))continue;
        try {text.blendMode=originals[index];if(text.blendMode!==originals[index])throw new Error('blend_probe_restore_readback_failed');result.restoredNodeIds.push(text.id);}
        catch(error){result.status='FAIL';result.issues.push({code:String(error.message),reference:text.id});}
      }
      try {
        result.observations.restored=snapshot();await raster('restored');
        result.originalObservedStateRestored=JSON.stringify(result.observations.before)===JSON.stringify(result.observations.restored);
        if(!result.originalObservedStateRestored)throw new Error('blend_probe_observed_state_not_restored');
      } catch(error){result.status='FAIL';result.issues.push({code:String(error.message)});}
    }
  }
  return result;
}
