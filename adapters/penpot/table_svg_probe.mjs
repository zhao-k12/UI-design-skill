// Diagnostic raster of the unmodified native SVG; original native PNG is retained.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {extractRuntime} from '../../component-builder/runtime-renderer/extract.mjs';
import {ROOT,hash,jsonFile} from '../../component-builder/source-reader/source-lock.mjs';

export async function probeTableSvg(capturePath,fontPath,expectedFontHash,outputPath) {
  const output=resolve(outputPath),input=resolve(capturePath);
  if(!output.startsWith(resolve(ROOT,'artifacts')+'\\')&&!output.startsWith(resolve(ROOT,'artifacts')+'/'))throw Error('probe_output_must_be_artifacts');
  if(input.startsWith(output)||resolve(fontPath).startsWith(output))throw Error('probe_input_overlap');
  if((await readdir(output).catch(e=>{if(e.code==='ENOENT')return [];throw e;})).length)throw Error('probe_output_not_empty');
  const receipt=await jsonFile(input),native=receipt.result;
  if(receipt.status!=='CAPTURED'||native.status!=='CAPTURED'||native.platform!=='penpot'||native.logicalId!=='data.table.default'||native.createdNodeIds.length||native.mutatedNodeIds.length)throw Error('invalid_native_table_capture');
  const svg=Buffer.from(native.nativeSvgBase64,'base64').toString('utf8'),font=await readFile(fontPath);
  if(hash(font)!==expectedFontHash)throw Error('probe_font_hash_mismatch');
  const urls=[...svg.matchAll(/src: url\((https:\/\/design\.penpot\.app\/assets\/by-id\/[0-9a-f-]{36})\) format\('woff'\)/g)].map(m=>m[1]);
  if(urls.length!==1||/<!|<\?|<script|<foreignObject|\son\w+=/i.test(svg))throw Error('unsupported_native_svg_resource');
  const reference=await jsonFile(join(ROOT,'adapters/figma/metadata/table-reference/component_ir.json'));
  await mkdir(output,{recursive:true});let sample;
  const {result}=await extractRuntime(output,{casesPath:join(ROOT,'component-builder/runtime-renderer/table-cases.json'),harnessPath:join(ROOT,'component-builder/runtime-renderer/table-harness.js'),observePage:async page=>{
    const sandbox=await page.context().newPage();
    await sandbox.route('**/*',route=>route.request().url()===urls[0]?route.fulfill({body:font,contentType:'font/woff'}):route.abort());
    try {
      await sandbox.setContent('<html><head><style>html,body{margin:0;background:white}svg{display:block}</style></head><body></body></html>');
      const observation=await sandbox.evaluate(async ({svg})=>{
        const doc=new DOMParser().parseFromString(svg,'image/svg+xml');
        const tags=new Set(['svg','style','g','rect','text','defs','pattern','clipPath','use']);
        const attrs=new Set(['width','height','viewBox','xmlns','xmlns:xlink','id','fill','version','class','x','y','rx','ry','transform','style','patternUnits','href','clip-path','dominant-baseline','textLength','lengthAdjust','opacity','stroke-width','stroke']);
        for(const el of doc.querySelectorAll('*')){
          if(el.namespaceURI!=='http://www.w3.org/2000/svg'||!tags.has(el.localName))throw Error('unsupported_native_svg_element');
          for(const a of el.attributes){
            if(!attrs.has(a.name))throw Error('unsupported_native_svg_attribute');
            if(a.name==='href'&&!/^#[\w-]+$/.test(a.value))throw Error('external_native_use');
            if(a.name==='opacity'&&a.value!=='1')throw Error('unsupported_native_opacity');
            if(a.name==='transform'&&a.value!=='matrix(1.000000, 0.000000, 0.000000, 1.000000, 0.000000, 0.000000)')throw Error('unsupported_native_transform');
          }
        }
        const root=doc.documentElement;
        if(root.getAttribute('width')!=='1392'||root.getAttribute('height')!=='144'||root.getAttribute('viewBox')!=='0 0 1392 144')throw Error('native_svg_geometry_changed');
        document.body.appendChild(document.importNode(root,true));
        await document.fonts.load('14px "PingFang SC"','张三启用管理员李四编辑王五停用访客');await document.fonts.ready;
        const texts=[...document.querySelectorAll('svg text')];
        const expected=['张三','启用','管理员','李四','启用','编辑','王五','停用','访客'];
        if(texts.length!==9||JSON.stringify(texts.map(t=>t.textContent).sort())!==JSON.stringify(expected.sort()))throw Error('native_text_inventory_changed');
        const point=p=>({x:p.x,y:p.y});
        return {texts:texts.map(text=>{const box=text.getBBox(),style=getComputedStyle(text);return {
          characters:text.textContent,fontFamily:style.fontFamily,fontSize:style.fontSize,fontWeight:style.fontWeight,
          length:text.getComputedTextLength(),start:Array.from(text.textContent,(_,i)=>point(text.getStartPositionOfChar(i))),end:Array.from(text.textContent,(_,i)=>point(text.getEndPositionOfChar(i))),
          bbox:{x:box.x,y:box.y,width:box.width,height:box.height}};}),fontLoadStatus:document.fonts.check('14px "PingFang SC"','张三启用管理员李四编辑王五停用访客')};
      },{svg});
      const png=await sandbox.locator('svg').screenshot({animations:'disabled'});
      await writeFile(join(output,'native-svg.png'),png,{flag:'wx'});
      sample={...observation,svgSha256:hash(Buffer.from(svg)),pngSha256:hash(png),fontUrl:urls[0],fontSha256:hash(font)};
    } finally {await sandbox.close();}
  }});
  const matches=result.components.map(row=>{
    const old=reference.components.find(c=>c.logicalComponentId===row.logicalComponentId);
    return {logicalId:row.logicalComponentId,screenshotMatches:row.screenshot.sha256===old.screenshot.sha256,
      environmentMatches:JSON.stringify(row.environment)===JSON.stringify(old.environment)};
  });
  const report={status:matches.every(r=>r.screenshotMatches&&r.environmentMatches)?'OBSERVED':'REVIEW',
    scope:'penpot-native-svg-browser-diagnostic',nativeReceiptSha256:hash(await readFile(input)),
    referenceComponentIrSha256:hash(await readFile(join(ROOT,'adapters/figma/metadata/table-reference/component_ir.json'))),
    probeScriptSha256:hash(await readFile(new URL(import.meta.url))),sample,referenceMatches:matches,
    admissionEligible:false,fidelityGate:'NOT_RUN',
    limitations:['The font resource is served from the hash-verified local font container, not a remote download.',
      'Browser SVG raster is diagnostic; native PNG remains the production screenshot.']};
  await writeFile(join(output,'svg-probe.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const report=await probeTableSvg(...process.argv.slice(2));console.log(JSON.stringify(report));
}
