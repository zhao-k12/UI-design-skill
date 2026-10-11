// Read-only capability probe using exact names obtained from source font tables.
async function probeSourceFontLoading(api,request) {
  const report={scope:'figma_source_font_load_probe',status:'FAIL',fileReference:api.fileKey,
    createdNodeIds:[],mutatedNodeIds:[],admissionEligible:false,fidelityGate:'NOT_RUN',fonts:[],issues:[]};
  try {
    if(api.editorType!=='figma' || api.fileKey!==request.fileReference)throw new Error('font_probe_file_mismatch');
    if(!Array.isArray(request.fonts) || !request.fonts.length)throw new Error('font_probe_inputs_missing');
    for(const item of request.fonts) {
      if(!item.fontName?.family || !item.fontName?.style || !item.postScriptName || !/^[0-9a-f]{64}$/.test(item.sourceFileSha256))throw new Error('font_probe_source_identity_missing');
    }
    const available=await api.listAvailableFontsAsync();report.availableFontCount=available.length;
    for(const item of request.fonts) {
      const listed=available.some(font=>font.fontName.family===item.fontName.family && font.fontName.style===item.fontName.style);
      const result={fontName:item.fontName,postScriptName:item.postScriptName,sourceFileSha256:item.sourceFileSha256,
        listed,status:'MISSING',loadSucceeded:false};
      try {
        await api.loadFontAsync(item.fontName);
        result.loadSucceeded=true;
        result.status=listed?'LOAD_SUCCEEDED':'LOAD_SUCCEEDED_NOT_LISTED';
      } catch(error) { result.error=String(error.message); }
      report.fonts.push(result);
    }
    report.status=report.fonts.every(font=>font.status==='LOAD_SUCCEEDED')?'PASS':'REVIEW';
    report.limitations=['Successful loading alone does not establish glyph equality or font-file identity in Figma.',
      'Unlisted successful loads remain REVIEW; existing candidate guards are not bypassed.'];
  } catch(error) { report.issues.push({code:String(error.message)}); }
  return report;
}
