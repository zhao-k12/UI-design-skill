// Read native properties and export PNG without changing the canvas.
async function captureNativeComponent(api, request) {
  const result = {scope:'figma_native_component_capture', status:'FAIL', evidenceKind:'native-platform-export',
    evidenceScope:request.evidenceScope || 'production', captureId:request.captureId,
    exporterVersion:'figma-native-export-v0.1.1', fileReference:api.fileKey,
    logicalId:request.logicalId, componentReference:request.componentReference,
    createdNodeIds:[], mutatedNodeIds:[], admissionEligible:false, fidelityGate:'NOT_RUN', issues:[]};
  try {
    if (api.editorType !== 'figma' || api.fileKey !== request.fileReference) throw new Error('capture_file_mismatch');
    if (!request.captureId || !request.logicalId || !['production','test-fixture'].includes(result.evidenceScope)) throw new Error('invalid_capture_identity');
    const page = await api.getNodeByIdAsync(request.pageReference);
    if (!page || page.type !== 'PAGE') throw new Error('capture_page_missing');
    if (request.pageAlreadySelected) {
      if (api.currentPage?.id !== page.id) throw new Error('capture_current_page_mismatch');
    } else {
      await api.setCurrentPageAsync(page);
    }
    const root = await api.getNodeByIdAsync(request.componentReference);
    if (!root || root.type !== 'COMPONENT' || root.parent?.id !== page.id) throw new Error('capture_component_missing');
    // Load the existing text's actual font segments before inspecting/exporting it.
    const fonts = new Map();
    for (const node of root.findAllWithCriteria({types:['TEXT']})) {
      for (const segment of node.getStyledTextSegments(['fontName'])) {
        fonts.set(JSON.stringify(segment.fontName),segment.fontName);
      }
    }
    for (const font of fonts.values()) await api.loadFontAsync(font);
    const nodes=[];
    function copy(value) {
      if (value === api.mixed) return {nativeMixed:true};
      return JSON.parse(JSON.stringify(value));
    }
    function visit(node,parentReference) {
      const item={reference:node.id,parentReference,type:node.type,name:node.name,
        localBounds:{x:node.x,y:node.y,width:node.width,height:node.height},
        absoluteBounds:copy(node.absoluteBoundingBox),properties:{}};
      for (const key of ['visible','opacity','fills','strokes','strokeWeight','strokeAlign','cornerRadius',
          'effects','rotation','blendMode','isMask','clipsContent','layoutMode','layoutSizingHorizontal','layoutSizingVertical',
          'primaryAxisAlignItems','counterAxisAlignItems','itemSpacing','strokesIncludedInLayout',
          'paddingTop','paddingRight','paddingBottom','paddingLeft','layoutPositioning']) {
        if (key in node) item.properties[key]=copy(node[key]);
      }
      for(const key of ['strokeTopWeight','strokeRightWeight','strokeBottomWeight','strokeLeftWeight'])if(key in node)item.properties[key]=copy(node[key]);
      if (node.type === 'TEXT') {
        for (const key of ['characters','fontName','fontWeight','fontSize','lineHeight',
            'letterSpacing','textAutoResize','textAlignHorizontal','textAlignVertical']) item.properties[key]=copy(node[key]);
        for (const key of ['textCase','textDecoration','paragraphIndent','paragraphSpacing']) {
          if (key in node) item.properties[key]=copy(node[key]);
        }
      }
      nodes.push(item);
      if ('children' in node) for (const child of node.children) visit(child,node.id);
    }
    visit(root,null);
    if (!root.absoluteBoundingBox || root.width<=0 || root.height<=0) throw new Error('capture_empty_component');
    const bytes=await root.exportAsync({format:'PNG',constraint:{type:'SCALE',value:1},useAbsoluteBounds:true});
    result.nativeEvidence={pageReference:page.id,nodes,rootReference:root.id};
    result.raster={format:'PNG',scale:1,background:'native-transparent',bytes:Array.from(bytes)};
    result.limitations=['No per-glyph bounds or CSS-normalized measurements are inferred.',
      'Host result and hashes alone do not authenticate platform provenance.'];
    result.status='PASS';
  } catch(error) { result.issues.push({code:String(error.message)}); }
  return result;
}

async function finishCandidateCapture(api, built, request) {
  if (built.status !== 'PASS') return built;
  const componentReference=built.nativeObservation.componentReference;
  const capture=await captureNativeComponent(api,{...request,componentReference,
    captureId:request.captureId || `${request.fileReference}/${request.logicalId}/${componentReference}`,
    pageAlreadySelected:true});
  return {...built,status:capture.status,nativeCapture:capture,
    issues:[...(built.issues || []),...capture.issues]};
}


// Bounded transport of a single deterministic capture, never image processing.
function captureSha256(text,inputBytes){
  const bytes=inputBytes===undefined?Array.from(unescape(encodeURIComponent(text)),c=>c.charCodeAt(0)):Array.from(inputBytes);
  const length=bytes.length;bytes.push(128);while(bytes.length%64!==56)bytes.push(0);
  const bits=length*8;for(let i=7;i>=0;i--)bytes.push(i>=4?0:(bits>>>i*8)&255);
  const constants=[],initial=[];let prime=2;
  while(constants.length<64){let valid=true;for(let d=2;d*d<=prime;d++)if(prime%d===0){valid=false;break;}
    if(valid){if(initial.length<8)initial.push((Math.sqrt(prime)%1*4294967296)|0);constants.push((Math.cbrt(prime)%1*4294967296)|0);}prime++;}
  const rotate=(x,n)=>(x>>>n)|(x<<(32-n));const hash=initial.slice();
  for(let offset=0;offset<bytes.length;offset+=64){const w=[];for(let i=0;i<16;i++)w[i]=(bytes[offset+i*4]<<24)|(bytes[offset+i*4+1]<<16)|(bytes[offset+i*4+2]<<8)|bytes[offset+i*4+3];
    for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=(w[i-16]+(rotate(a,7)^rotate(a,18)^(a>>>3))+w[i-7]+(rotate(b,17)^rotate(b,19)^(b>>>10)))|0;}
    let[a,b,c,d,e,f,g,h]=hash;for(let i=0;i<64;i++){const t1=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[i]+w[i])|0;const t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))|0;h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}
    [a,b,c,d,e,f,g,h].forEach((value,i)=>hash[i]=(hash[i]+value)|0);
  }
  return hash.map(n=>(n>>>0).toString(16).padStart(8,'0')).join('');
}
function captureTransportPiece(result,index){
  if(result.status!=='PASS')return result;
  const raw=JSON.stringify(result),chunkSize=6500,count=Math.ceil(raw.length/chunkSize);
  if(!Number.isInteger(index)||index<0||index>=count)throw new Error('invalid_capture_transport_piece');
  return{scope:'figma_capture_transport_piece',status:'PASS',index,count,totalCharacters:raw.length,
    captureSha256:captureSha256(raw),chunk:raw.slice(index*chunkSize,(index+1)*chunkSize)};
}


await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('0:1'));const rows=[];for(const [logicalId,componentReference] of [['form.input.default.medium','12:8'],['form.select.default.medium','12:15'],['action.button.primary.medium','18:5'],['data.table.default','28:3']]){const result=await captureNativeComponent(figma,{fileReference:figma.fileKey,pageReference:'0:1',pageAlreadySelected:true,captureId:'task017-current-source-'+logicalId,logicalId,componentReference});if(result.status!=='PASS')return result;const bytes=new Uint8Array(result.raster.bytes);delete result.raster.bytes;result.nativePngBase64=figma.base64Encode(bytes);result.textOutlines=[];for(const n of (await figma.getNodeByIdAsync(componentReference)).findAllWithCriteria({types:['TEXT']})){result.textOutlines.push({reference:n.id,characters:n.characters,svg:await n.exportAsync({format:'SVG_STRING',svgOutlineText:true,useAbsoluteBounds:true})});}rows.push(result);}return captureTransportPiece({status:'PASS',createdNodeIds:[],mutatedNodeIds:[],sources:rows},0);
