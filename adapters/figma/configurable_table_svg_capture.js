async function captureConfigurableTableSvg(api,request){
  const capture=await captureConfigurableFigmaTable(api,request);
  if(capture.status!=='PASS')return capture;
  const root=await api.getNodeByIdAsync(request.componentReference);
  const svg=await root.exportAsync({format:'SVG_STRING',svgOutlineText:true,useAbsoluteBounds:true});
  const after=await captureConfigurableFigmaTable(api,request);
  if(JSON.stringify(capture)!==JSON.stringify(after))throw Error('table_svg_capture_changed');
  return {scope:'figma_native_component_svg_diagnostic',status:'PASS',fileReference:api.fileKey,pageReference:request.pageReference,observations:[{logicalId:request.logicalId,componentReference:root.id,width:root.width,height:root.height,svg}],nativePngSha256:captureSha256('',capture.raster.bytes),nativeEvidenceJsonSha256:captureSha256(JSON.stringify(capture.nativeEvidence)),createdNodeIds:[],mutatedNodeIds:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
}
