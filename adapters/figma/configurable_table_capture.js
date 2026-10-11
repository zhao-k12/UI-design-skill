// Two independent property/PNG reads must agree before any transport piece.
async function captureConfigurableFigmaTable(api,request){
  const first=await captureNativeComponent(api,request);if(first.status!=='PASS')return first;
  const second=await captureNativeComponent(api,request);if(second.status!=='PASS')return second;
  if(JSON.stringify(first)!==JSON.stringify(second))throw Error('configurable_table_capture_changed');
  for(const item of first.nativeEvidence.nodes)if(item.type==='TEXT'){
    const node=await api.getNodeByIdAsync(item.reference);
    for(const key of ['textStyleId','textTruncation','maxLines'])item.properties[key]=node[key];
  }
  return first;
}
