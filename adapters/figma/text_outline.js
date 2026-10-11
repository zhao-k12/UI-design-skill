// Read-only native Text outline evidence. Never creates or flattens nodes.
async function captureTextOutlines(api, request) {
  const result={scope:'figma_native_text_outline_diagnostic',status:'FAIL',fileReference:api.fileKey,
    pageReference:request.pageReference,observations:[],createdNodeIds:[],mutatedNodeIds:[],
    admissionEligible:false,fidelityGate:'NOT_RUN',issues:[]};
  try {
    if(api.editorType!=='figma'||api.fileKey!==request.fileReference)throw new Error('outline_file_mismatch');
    if(!Array.isArray(request.textReferences)||!request.textReferences.length||new Set(request.textReferences).size!==request.textReferences.length)throw new Error('invalid_outline_selection');
    const page=await api.getNodeByIdAsync(request.pageReference);
    if(!page||page.type!=='PAGE')throw new Error('outline_page_missing');
    await api.setCurrentPageAsync(page);
    const texts=[];
    for(const id of request.textReferences) {
      const text=await api.getNodeByIdAsync(id);
      if(!text||text.type!=='TEXT')throw new Error('outline_text_missing');
      let parent=text.parent;while(parent&&parent.type!=='PAGE')parent=parent.parent;
      if(parent?.id!==page.id)throw new Error('outline_text_page_mismatch');
      texts.push(text);
    }
    for(const text of texts) {
      for(const segment of text.getStyledTextSegments(['fontName']))await api.loadFontAsync(segment.fontName);
      const svg=await text.exportAsync({format:'SVG_STRING',svgOutlineText:true,useAbsoluteBounds:true});
      if(typeof svg!=='string'||!svg.startsWith('<svg')||svg.length>1000000)throw new Error('invalid_outline_export');
      const value=item=>item===api.mixed?{nativeMixed:true}:item;
      result.observations.push({textReference:text.id,characters:text.characters,fontName:value(text.fontName),
        fontWeight:value(text.fontWeight),fontSize:value(text.fontSize),lineHeight:value(text.lineHeight),
        absoluteBounds:text.absoluteBoundingBox,absoluteRenderBounds:text.absoluteRenderBounds,svg});
    }
    result.status='PASS';
  } catch(error) {result.issues.push({code:String(error.message)});}
  return result;
}
