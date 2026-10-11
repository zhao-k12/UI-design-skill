"""Serve the project's own read-only diagnostic plugin on browser-safe loopback."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import random
import secrets
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]


def assets(base, target_file, nonce):
    discovery = (ROOT / "adapters/penpot/discovery.js").read_text(encoding="utf-8")
    plugin = discovery + "\n" + "const targetFile = " + json.dumps(target_file) + ";\n"
    plugin += "penpot.ui.open('TASK-010 实际环境检查'," + json.dumps(base + "/index.html") + ",{width:440,height:280});\n"
    plugin += """penpot.ui.onMessage(message => {
      if (message?.type !== 'task010-inspect') return;
      try {
        if (penpot.currentFile?.id !== targetFile) throw new Error('target_file_mismatch');
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result:discoverPenpotHost(penpot)});
      } catch (error) { penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)}); }
    });
    """
    client = "const nonce = " + json.dumps(nonce) + ";\n" + """
    const button=document.getElementById('inspect'), status=document.getElementById('status');
    button.onclick=()=>{button.disabled=true;status.textContent='正在读取实际文件…';parent.postMessage({type:'task010-inspect'},'https://design.penpot.app');};
    window.addEventListener('message',async event=>{
      if(event.source!==parent || event.origin!=='https://design.penpot.app' || event.data?.type!=='task010-result')return;
      try {
        const response=await fetch('/receipt',{method:'POST',headers:{'Content-Type':'application/json','X-Task-Nonce':nonce},body:JSON.stringify(event.data)});
        if(!response.ok)throw new Error('本机记录保存失败');
        const result=event.data.result;
        status.textContent=event.data.status==='CAPTURED'?`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`:event.data.error;
      }catch(error){status.textContent=String(error);}finally{button.disabled=false;}
    });
    """
    html = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>TASK-010 实际环境检查</title>
    <style>body{font:15px sans-serif;padding:20px;background:#fff;color:#222}button{padding:10px 18px}p{line-height:1.5}</style>
    <h3>实际环境检查</h3><p>仅读取当前验收文件的字体和组件清单，记录保存到本机。</p>
    <button id="inspect">读取实际环境</button><p id="status">等待读取</p><script src="client.js"></script></html>"""
    manifest = {"name":"UI Design Skill · TASK-010 检查", "description":"项目自建的文件限定只读环境检查；结果只保存本机",
                "version":2, "code":"plugin.js", "icon":"icon.svg", "permissions":["content:read","library:read"]}
    icon = '<svg xmlns="http://www.w3.org/2000/svg" width="56" height="56"><rect width="56" height="56" rx="10" fill="#2d8cf0"/><text x="28" y="36" text-anchor="middle" fill="white" font-size="26">UI</text></svg>'
    return {"/manifest.json":("application/json",json.dumps(manifest,ensure_ascii=False)),
            "/plugin.js":("text/javascript",plugin), "/index.html":("text/html",html),
            "/client.js":("text/javascript",client), "/icon.svg":("image/svg+xml",icon)}


def candidate_assets(base,target_file,nonce,spec,readback=None,observed_assets=None):
    if spec.get('fileReference')!=target_file or spec.get('logicalId') not in ('action.button.primary.medium','form.input.default.medium','form.select.default.medium','data.table.default'):raise ValueError('candidate_target_mismatch')
    from adapters.penpot.component_candidate import prepare_button_candidate, prepare_input_candidate, prepare_select_candidate
    is_input=spec['logicalId']=='form.input.default.medium'
    is_select=spec['logicalId']=='form.select.default.medium'
    is_table=spec['logicalId']=='data.table.default'
    if is_table:
        from adapters.penpot.table_candidate import prepare_table_candidate
        expected=prepare_table_candidate(ROOT/'adapters/figma/metadata/table-reference',target_file,spec['pageReference'])
    elif is_select:expected=prepare_select_candidate(ROOT/'adapters/figma/metadata/official-fixture-reference',target_file,spec['pageReference'])
    else:expected=prepare_input_candidate(ROOT/'adapters/figma/metadata/official-fixture-reference',ROOT/'adapters/figma/metadata/official-runtime-render-state-evidence.json',target_file,spec['pageReference']) if is_input else prepare_button_candidate(ROOT/'adapters/figma/metadata/official-fixture-reference',target_file,spec['pageReference'])
    if spec!=expected:raise ValueError('candidate_source_plan_changed')
    result=assets(base,target_file,nonce)
    manifest=json.loads(result['/manifest.json'][1]);manifest.update(name='UI Design Skill · 原生 Button 候选',
        description='仅在指定 TASK-010 文件建立一个官方源 Button 候选并读取原生导出；不进行正式准入',
        permissions=['content:write','library:write'])
    result['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    runtime=(ROOT/'adapters/penpot/component_candidate.js').read_text(encoding='utf-8')
    if is_select:runtime+='\n'+(ROOT/'adapters/penpot/select_candidate.js').read_text(encoding='utf-8')
    if is_table:runtime+='\n'+(ROOT/'adapters/penpot/table_candidate.js').read_text(encoding='utf-8')
    capture=(ROOT/'adapters/penpot/component_capture.js').read_text(encoding='utf-8')
    if readback is not None and (readback.get('status')!='CANDIDATE_CREATED' or readback.get('fileReference')!=target_file or
        readback.get('pageReference')!=spec['pageReference'] or readback.get('componentIrSha256')!=spec['componentIrSha256']):raise ValueError('candidate_readback_mismatch')
    plugin=result['/plugin.js'][1]+runtime+'\n'+capture+'\nconst candidateSpec='+json.dumps(spec,ensure_ascii=False)+';\nlet lastCandidate='+json.dumps(readback,ensure_ascii=False)+';\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['task010-build-button','task010-capture-button','task010-outline-button','task010-normalize-paint','task010-normalize-border'].includes(message?.type))return;
      try{
        if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');
        let result;
        if(message.type==='task010-build-button')result=lastCandidate=await buildPenpotButtonCandidate(penpot,candidateSpec);
        else {if(lastCandidate?.status!=='CANDIDATE_CREATED')throw new Error('create_candidate_first');result=message.type==='task010-normalize-border'?await normalizePenpotButtonBorder(penpot,lastCandidate,candidateSpec):message.type==='task010-normalize-paint'?await normalizePenpotButtonPaint(penpot,lastCandidate,candidateSpec):message.type==='task010-outline-button'?await probePenpotTextOutline(penpot,lastCandidate):await capturePenpotButtonCandidate(penpot,lastCandidate);}
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    result['/plugin.js']=('text/javascript',plugin)
    if is_table:
        plugin=plugin.replace('await buildPenpotButtonCandidate(penpot,candidateSpec)','await buildPenpotTableCandidate(penpot,candidateSpec)')
        plugin=plugin.replace("if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');\n        let result;", "if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');\n        if(!['task010-build-button','task010-capture-button'].includes(message.type))throw new Error('unsupported_table_action');\n        let result;")
        result['/plugin.js']=('text/javascript',plugin)
    if is_select:
        plugin=plugin.replace('await buildPenpotButtonCandidate(penpot,candidateSpec)','await buildPenpotSelectCandidate(penpot,candidateSpec)')
        plugin=plugin.replace("if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');\n        let result;", "if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');\n        if(!['task010-build-button','task010-capture-button'].includes(message.type))throw new Error('unsupported_select_action');\n        let result;")
        result['/plugin.js']=('text/javascript',plugin)
    if is_input:
        plugin=plugin.replace('await buildPenpotButtonCandidate(penpot,candidateSpec)','await buildPenpotInputCandidate(penpot,candidateSpec)')
        plugin=plugin.replace("if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');\n        let result;", "if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');\n        if(!['task010-build-button','task010-capture-button','task010-normalize-border'].includes(message.type))throw new Error('unsupported_input_action');\n        let result;")
        plugin=plugin.replace('await normalizePenpotButtonBorder(penpot,lastCandidate,candidateSpec)','await orderPenpotInputPaint(penpot,lastCandidate,candidateSpec)')
        result['/plugin.js']=('text/javascript',plugin)
    client=result['/client.js'][1]+'''
    document.getElementById('build').onclick=()=>{status.textContent='正在建立源组件候选…';parent.postMessage({type:'task010-build-button'},'https://design.penpot.app');};
    document.getElementById('capture').onclick=()=>{status.textContent='正在读取原生导出…';parent.postMessage({type:'task010-capture-button'},'https://design.penpot.app');};
    document.getElementById('outline').onclick=()=>{status.textContent='正在测量独立诊断字形…';parent.postMessage({type:'task010-outline-button'},'https://design.penpot.app');};
    document.getElementById('paint').onclick=()=>{status.textContent='正在合并同色不透明区域…';parent.postMessage({type:'task010-normalize-paint'},'https://design.penpot.app');};
    document.getElementById('border').onclick=()=>{status.textContent='正在建立来源边框中线几何…';parent.postMessage({type:'task010-normalize-border'},'https://design.penpot.app');};
    '''
    client=client.replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`",
        "result.fonts?`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。`:`实际结果：${result.status}。保真检查尚未执行。`")
    result['/client.js']=('text/javascript',client)
    result['/index.html']=('text/html',result['/index.html'][1].replace('<button id="inspect">',
        '<button id="build">建立官方 Button 候选</button><button id="capture">读取原生候选</button><button id="outline">测量实际字形</button><button id="paint">合并同色区域</button><button id="border">建立边框中线</button><button id="inspect">'))
    result['/index.html']=('text/html',result['/index.html'][1].replace(
        '仅读取当前验收文件的字体和组件清单，记录保存到本机。',
        '在指定验收文件建立官方 Button 候选并读取实际导出。诊断结果保存到本机，通过完整保真检查后才能准入。'))
    # Exact font URLs already observed in the authorized workspace resource inventory.
    import re
    observed_assets=observed_assets or []
    if any(not isinstance(url,str) or not re.fullmatch(r'https://design\.penpot\.app/assets/by-id/[0-9a-f-]{36}',url) for url in observed_assets):raise ValueError('invalid_observed_asset_url')
    links='<p>已观察资源诊断：</p>'+''.join(f'<a href="{url}" download>已观察资源 {i+1}</a> ' for i,url in enumerate(observed_assets))
    result['/index.html']=('text/html',result['/index.html'][1].replace('</html>',links+'</html>'))
    if is_input:
        result['/index.html']=('text/html',result['/index.html'][1].replace('Button','Input').replace('<button id="outline">','<button hidden id="outline">').replace('<button id="paint">','<button hidden id="paint">').replace('建立边框中线</button>','校正背景图层顺序</button>'))
        manifest.update(name='UI Design Skill · 原生 Input 候选',description='指定验收文件内的官方源 Input 候选；原生基线和保真待验证')
        result['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    if is_table:
        result['/index.html']=('text/html',result['/index.html'][1].replace('Button','Table').replace('<button id="outline">','<button hidden id="outline">').replace('<button id="paint">','<button hidden id="paint">').replace('<button id="border">','<button hidden id="border">'))
        manifest.update(name='UI Design Skill · 原生 Table 候选',description='指定文件内的官方源静态 Table 候选；尚未通过保真验证')
        result['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    if is_select:
        result['/index.html']=('text/html',result['/index.html'][1].replace('Button','Select').replace('<button id="outline">','<button hidden id="outline">').replace('<button id="paint">','<button hidden id="paint">').replace('<button id="border">','<button hidden id="border">'))
        manifest.update(name='UI Design Skill · 原生 Select 候选',description='指定文件内的官方源 Select 候选；文字与箭头均待保真验证')
        result['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    return result


def icon_assets(base,target_file,nonce,payload,readback=None):
    from adapters.penpot.icons import prepare_icons
    if payload!=prepare_icons(target_file,payload['pageReference']):raise ValueError('icon_source_plan_changed')
    if readback is not None and (readback.get('status')!='ICONS_CREATED' or readback.get('fileReference')!=target_file or readback.get('pageReference')!=payload['pageReference'] or readback.get('registrySha256')!=payload['registrySha256']):raise ValueError('icon_readback_mismatch')
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest.update(name='UI Design Skill · 官方图标候选',description='指定验收文件中的两份原始 Remix SVG 原生导入及独立capture',permissions=['content:write','library:write'])
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]+(ROOT/'adapters/penpot/icon_library.js').read_text(encoding='utf-8')+'\nconst iconPayload='+json.dumps(payload,ensure_ascii=False)+';\nlet iconReadback='+json.dumps(readback,ensure_ascii=False)+';\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['task010-build-icons','task010-capture-icons','task010-content-icons','task010-restore-icons'].includes(message?.type))return;
      try{let result;
        if(message.type==='task010-build-icons')result=iconReadback=await buildPenpotIcons(penpot,iconPayload);
        else{if(iconReadback?.status!=='ICONS_CREATED')throw new Error('create_icons_first');result=message.type==='task010-restore-icons'?await restorePenpotIconSourcePaths(penpot,iconReadback,iconPayload):await capturePenpotIcons(penpot,iconReadback,{contentRaster:message.type==='task010-content-icons'});}
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","result.fonts?`读取完成：${result.fonts.length} 个字体系列。`:`实际结果：${result.status}。源映射验证尚未执行。`")
    client+="\ndocument.getElementById('build').onclick=()=>parent.postMessage({type:'task010-build-icons'},'https://design.penpot.app');document.getElementById('capture').onclick=()=>parent.postMessage({type:'task010-capture-icons'},'https://design.penpot.app');"
    client+="\ndocument.getElementById('restore').onclick=()=>parent.postMessage({type:'task010-restore-icons'},'https://design.penpot.app');"
    client+="\ndocument.getElementById('content').onclick=()=>parent.postMessage({type:'task010-content-icons'},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html',served['/index.html'][1].replace('<button id="inspect">','<button id="build">导入两份官方 SVG</button><button id="capture">读取原生图标</button><button id="content">读取原生内容组</button><button id="restore">在原点恢复来源路径</button><button id="inspect">').replace('仅读取当前验收文件的字体和组件清单，记录保存到本机。','在指定验收文件导入两份原始官方SVG；结果保存本机，独立检查通过后才能登记。'))
    return served


def fixed_page_plan(target_file):
    from importlib import import_module
    from adapters.component_bindings import ComponentBindings
    from adapters.penpot.compiler import prepare
    read=lambda path:json.loads((ROOT/path).read_bytes())
    tokens=import_module('core.design-rules.tokens').TokenRegistry(read('registries/tokens/default.json'))
    components=import_module('core.component-resolver.registry').ComponentRegistry(read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
    bindings=ComponentBindings(read('adapters/penpot/metadata/component-bindings.json'),components,platform='penpot')
    icons=import_module('core.icon-resolver.registry').IconRegistry(import_module('icon-manager.remix-sync.manager').current())
    report=prepare(read('examples/adapter-fidelity-acceptance.ui-ir.json'),tokens,components,bindings,icons,read('adapters/penpot/metadata/icon-bindings.json'),read('adapters/penpot/metadata/font-bindings.json'),file_reference=target_file,native_fidelity=read('adapters/penpot/metadata/native-fidelity.json'))
    if report['status']!='PASS':raise ValueError('fixed_page_preflight_failed')
    return report['plan']


def page_assets(base,target_file,nonce,plan,readback=None,instances_readback=None):
    if plan!=fixed_page_plan(target_file):raise ValueError('fixed_page_plan_changed')
    if readback is not None and (readback.get('status')!='EXECUTED' or readback.get('fileReference')!=target_file or readback.get('uiIrSha256')!=plan['uiIrSha256']):raise ValueError('fixed_page_readback_mismatch')
    if instances_readback is not None and (not readback or instances_readback.get('fileReference')!=target_file or instances_readback.get('pageReference')!=readback['pageReference'] or instances_readback.get('rootReference')!=readback['rootReference'] or instances_readback.get('scope')!='production-native-instance-capture'):raise ValueError('fixed_instances_readback_mismatch')
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest.update(name='UI Design Skill · 固定列表验收',description='同一固定UI-IR在指定验收文件的原生组装与独立读取',permissions=['content:write','library:write'])
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    payload={key:value for key,value in plan.items() if key!='pages'};payload.update(page=plan['pages'][0],pageReference=None)
    plugin=served['/plugin.js'][1]+(ROOT/'adapters/penpot/runtime.js').read_text(encoding='utf-8')+'\n'+(ROOT/'adapters/penpot/capture.js').read_text(encoding='utf-8')+'\nconst fixedPayload='+json.dumps(payload,ensure_ascii=False)+';\nlet fixedExecution='+json.dumps(readback,ensure_ascii=False)+';\n'
    plugin+=(ROOT/'adapters/penpot/page_recovery.js').read_text(encoding='utf-8')+'\n'
    plugin+=(ROOT/'adapters/penpot/page_instances.js').read_text(encoding='utf-8')+'\n'
    plugin+='\nlet previousInstances='+json.dumps(instances_readback,ensure_ascii=False)+';\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['task010-execute-page','task010-capture-page','task010-default-page','task010-page-instances','task010-reset-icon-copies'].includes(message?.type))return;
      try{let result;
        if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');
        if(message.type==='task010-execute-page'){
          if(fixedExecution)throw new Error('fixed_page_already_executed');
          result=fixedExecution=await executePenpotAdapter(penpot,fixedPayload);
        }else{
          if(fixedExecution?.status!=='EXECUTED')throw new Error('execute_fixed_page_first');
          result=message.type==='task010-reset-icon-copies'?await resetPenpotIconCopies(penpot,fixedPayload,fixedExecution):message.type==='task010-page-instances'?(previousInstances=await capturePenpotPageInstances(penpot,fixedPayload,fixedExecution,previousInstances)):message.type==='task010-default-page'?await restorePenpotPageDefaults(penpot,fixedPayload,fixedExecution):await capturePenpotOutput(penpot,fixedExecution);
        }
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","result.fonts?`读取完成：${result.fonts.length} 个字体系列。`:`实际结果：${result.status}。最终验收尚未完成。`")
    client+="\ndocument.getElementById('execute').onclick=()=>{status.textContent='正在组装固定列表页…';parent.postMessage({type:'task010-execute-page'},'https://design.penpot.app');};document.getElementById('capture').onclick=()=>{status.textContent='正在独立读取原生结果…';parent.postMessage({type:'task010-capture-page'},'https://design.penpot.app');};"
    client+="\ndocument.getElementById('defaults').onclick=()=>parent.postMessage({type:'task010-default-page'},'https://design.penpot.app');"
    client+="\ndocument.getElementById('instances').onclick=()=>{status.textContent='正在读取六个真实实例…';parent.postMessage({type:'task010-page-instances'},'https://design.penpot.app');};"
    client+="\ndocument.getElementById('reset-icons').onclick=()=>parent.postMessage({type:'task010-reset-icon-copies'},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html',served['/index.html'][1].replace('<button id="inspect">','<button id="execute">组装固定列表页</button><button id="capture">读取固定列表页</button><button id="instances">读取六个真实实例</button><button id="defaults">显式恢复来源默认值</button><button id="inspect">').replace('仅读取当前验收文件的字体和组件清单，记录保存到本机。','严格按已验证固定UI-IR组装独立列表页；读取结果保存本机，最终验收独立执行。'))
    served['/index.html']=('text/html',served['/index.html'][1].replace('<button id="inspect">','<button id="reset-icons">重置关联图标实例</button><button id="inspect">'))
    return served


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-file",required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--candidate",type=Path)
    parser.add_argument("--icons",type=Path)
    parser.add_argument("--page-plan",type=Path)
    parser.add_argument("--instances-readback",type=Path)
    parser.add_argument("--candidate-readback",type=Path)
    parser.add_argument("--observed-assets",type=Path)
    parser.add_argument("--port",type=int)
    args=parser.parse_args()
    if args.port is not None and not 49152<=args.port<=65535:parser.error('Port must be browser-safe high loopback port')
    output=args.output_dir.resolve()
    if not output.is_relative_to((ROOT/"artifacts").resolve()): parser.error("Output must stay in project artifacts")
    if output.exists() and any(output.iterdir()): parser.error("Choose an empty diagnostic output directory")
    output.mkdir(parents=True,exist_ok=True)
    nonce=secrets.token_hex(24); config={}; receipts=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*items): pass
        def reply(self,status,data,mime="application/json"):
            data=data.encode("utf-8") if isinstance(data,str) else data
            self.send_response(status);self.send_header("Content-Type",mime+"; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin","https://design.penpot.app")
            self.send_header("Access-Control-Allow-Private-Network","true")
            self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
        def do_OPTIONS(self):
            self.send_response(204);self.send_header("Access-Control-Allow-Origin","https://design.penpot.app")
            self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers","Content-Type,X-Task-Nonce")
            self.send_header("Access-Control-Allow-Private-Network","true");self.end_headers()
        def do_GET(self):
            item=config["assets"].get(urlparse(self.path).path)
            if item:self.reply(200,item[1],item[0])
            else:self.reply(404,b'{}')
        def do_POST(self):
            if (self.path!="/receipt" or self.headers.get("Origin")!=config["base"] or
                not secrets.compare_digest(self.headers.get("X-Task-Nonce",""),nonce)):
                self.reply(403,b'{}');return
            try:
                length=int(self.headers.get("Content-Length","0"))
                if not 0<length<=8*1024*1024:raise ValueError("invalid_receipt_size")
                data=json.loads(self.rfile.read(length))
                if data.get("type")!="task010-result":raise ValueError("invalid_receipt_type")
                if data.get("status")=="CAPTURED" and data.get("result",{}).get("fileReference")!=args.target_file:raise ValueError("receipt_file_mismatch")
                filename=f"discovery-{len(receipts)+1}.json"
                with (output/filename).open('xb') as stream:stream.write((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
                receipts.append(filename);print(json.dumps({"receipt":filename,"status":data.get("status")}),flush=True)
                self.reply(200,b'{"saved":true}')
            except (ValueError,TypeError,OSError):self.reply(400,b'{}')
    server=None
    for _ in range(16):
        try:server=ThreadingHTTPServer(('127.0.0.1',args.port or random.randint(49152,65535)),Handler);break
        except OSError:
            if args.port is not None:raise
            continue
    if not server:raise RuntimeError("No free browser-safe loopback port")
    base=f"http://127.0.0.1:{server.server_port}"
    readback=json.loads(args.candidate_readback.read_text(encoding='utf-8'))['result'] if args.candidate_readback else None
    observed=json.loads(args.observed_assets.read_text(encoding='utf-8')) if args.observed_assets else None
    if observed and observed.get('fileReference')!=args.target_file:raise ValueError('observed_asset_file_mismatch')
    if sum(bool(v) for v in (args.icons,args.candidate,args.page_plan))>1:raise ValueError('choose_one_native_operation')
    instances=json.loads(args.instances_readback.read_bytes())['result'] if args.instances_readback else None
    if instances is not None and not args.page_plan:raise ValueError('instances_require_fixed_page')
    served=page_assets(base,args.target_file,nonce,json.loads(args.page_plan.read_text(encoding='utf-8')),readback,instances) if args.page_plan else icon_assets(base,args.target_file,nonce,json.loads(args.icons.read_text(encoding='utf-8')),readback) if args.icons else candidate_assets(base,args.target_file,nonce,json.loads(args.candidate.read_text(encoding='utf-8')),readback,observed.get('urls') if observed else None) if args.candidate else assets(base,args.target_file,nonce)
    config.update(base=base,assets=served)
    (output/'host-manifest.json').write_bytes((json.dumps({"baseUrl":base,"targetFile":args.target_file,"permissions":json.loads(served['/manifest.json'][1])['permissions']},indent=2)+'\n').encode())
    print(json.dumps({"manifestUrl":base+'/manifest.json',"targetFile":args.target_file}),flush=True)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=="__main__":main()
