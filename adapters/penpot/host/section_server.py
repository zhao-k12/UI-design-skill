"""Narrow loopback native-content fixture host; preserves the TASK-010 host."""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse

from adapters.penpot.host.server import assets, ROOT
from adapters.penpot.compiler import prepare
from adapters.component_bindings import ComponentBindings


def validation_plans(target_file):
    read=lambda name:json.loads((ROOT/name).read_bytes())
    tokens=import_module('core.design-rules.tokens').TokenRegistry(read('registries/tokens/default.json'))
    components=import_module('core.component-resolver.registry').ComponentRegistry(read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
    bindings=ComponentBindings(read('adapters/penpot/metadata/component-bindings.json'),components,platform='penpot')
    icons=import_module('core.icon-resolver.registry').IconRegistry(import_module('icon-manager.remix-sync.manager').current())
    document=read('examples/adapter-fidelity-acceptance.ui-ir.json');document['documentId']='task015-native-section-acceptance'
    updated=deepcopy(document)
    def walk(n):
        if n['id']=='button.query':n['slots']={'label':[{'id':'button.query.label','type':'Text','text':'导出'}]}
        for c in n.get('children',[]):walk(c)
    walk(updated['pages'][0])
    def compile(doc):
        result=prepare(doc,tokens,components,bindings,icons,read('adapters/penpot/metadata/icon-bindings.json'),read('adapters/penpot/metadata/font-bindings.json'),file_reference=target_file,native_fidelity=read('adapters/penpot/metadata/native-fidelity.json'))
        if result['status']!='PASS':raise ValueError('section_fixture_preflight_failed: '+str(result['issues']))
        return result['plan']
    return {'baseline':compile(document),'updated':compile(updated),'baselineUiIr':document,'updatedUiIr':updated}


def section_assets(base,target_file,nonce,readback=None):
    plans=validation_plans(target_file);baseline,changed=plans['baseline'],plans['updated']
    def payload(plan):
        return {**{k:v for k,v in plan.items() if k!='pages'},'page':plan['pages'][0],'pageReference':None}
    if readback and (readback.get('status')!='EXECUTED' or readback.get('fileReference')!=target_file or readback.get('uiIrSha256')!=baseline['uiIrSha256']):raise ValueError('section_execution_mismatch')
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest.update(name='UI Design Skill · 固定列表验收',description='项目自建的独立局部内容验收；不修改TASK-010验收页',permissions=['content:write','library:write'])
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]
    for name in ('runtime.js','content_runtime.js','section_patch.js'):plugin+='\n'+(ROOT/'adapters/penpot'/name).read_text(encoding='utf-8')
    plugin+='\nconst baselinePayload='+json.dumps(payload(baseline),ensure_ascii=False)+';\nconst changedPayload='+json.dumps(payload(changed),ensure_ascii=False)+';\nlet sectionExecution='+json.dumps(readback,ensure_ascii=False)+';let beforePatch=null;\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['task015-baseline','task015-before','task015-patch','task015-after'].includes(message?.type))return;
      try{let result;
        if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');
        if(message.type==='task015-baseline'){
          if(sectionExecution)throw new Error('section_baseline_already_exists');
          result=sectionExecution=await executePenpotAdapter(penpot,baselinePayload);
        }else{
          if(sectionExecution?.status!=='EXECUTED')throw new Error('section_baseline_required');
          if(message.type==='task015-before')result=beforePatch=await capturePenpotSectionPatch(penpot,sectionExecution);
          else if(message.type==='task015-after')result=await capturePenpotSectionPatch(penpot,sectionExecution);
          else{
            if(!beforePatch)throw new Error('independent_before_capture_required');
            const texts=beforePatch.nodes.filter(n=>n.type==='text'&&n.name==='official-source / action.button.primary.medium / 0.0');
            if(texts.length!==1)throw new Error('section_text_ambiguous');
            result=await patchPenpotSectionContent(penpot,changedPayload,sectionExecution,{
              baseUiIrSha256:baselinePayload.uiIrSha256,updatedUiIrSha256:changedPayload.uiIrSha256,
              expectedRevision:beforePatch.fileRevision,uiIrIds:['button.query'],sectionIds:['query'],
              expectedCharacters:{'button.query':{[texts[0].name]:texts[0].characters}}});
          }
        }
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","`结果：${result.status}，独立验收待执行。`")
    for action in ('baseline','before','patch','after'):client+=f"\ndocument.getElementById('{action}').onclick=()=>parent.postMessage({{type:'task015-{action}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html','''<!doctype html><html lang="zh"><meta charset="utf-8"><title>局部内容验收</title><style>body{font:15px sans-serif;padding:20px}button{padding:10px;margin:4px}</style><h3>局部内容验收</h3><p>独立验收页：修改查询区真实按钮文字，保留其他区块和原有位置。</p><button id="baseline">建立独立验收页</button><button id="before">读取修改前</button><button id="patch">仅更新查询区按钮</button><button id="after">独立读取修改后</button><button id="inspect">读取环境</button><p id="status">等待执行</p><script src="client.js"></script></html>''')
    return served


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--target-file',required=True);cli.add_argument('--output-dir',type=Path,required=True)
    cli.add_argument('--port',type=int,required=True);cli.add_argument('--candidate-readback',type=Path)
    args=cli.parse_args();output=args.output_dir.resolve()
    if not 49152<=args.port<=65535 or not output.is_relative_to((ROOT/'artifacts').resolve()):cli.error('Use a high loopback port and project artifact directory')
    if output.exists() and any(output.iterdir()):cli.error('Choose an empty output directory')
    output.mkdir(parents=True,exist_ok=True);nonce=secrets.token_hex(24);base=f'http://127.0.0.1:{args.port}'
    readback=json.loads(args.candidate_readback.read_bytes())['result'] if args.candidate_readback else None
    served=section_assets(base,args.target_file,nonce,readback);receipts=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*items):pass
        def reply(self,status,content,mime='application/json'):
            data=content.encode('utf-8') if isinstance(content,str) else content
            self.send_response(status);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Access-Control-Allow-Origin','https://design.penpot.app');self.send_header('Access-Control-Allow-Private-Network','true');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            item=served.get(urlparse(self.path).path)
            self.reply(200,item[1],item[0]) if item else self.reply(404,b'{}')
        def do_OPTIONS(self):
            self.send_response(204);self.send_header('Access-Control-Allow-Origin','https://design.penpot.app');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type,X-Task-Nonce');self.send_header('Access-Control-Allow-Private-Network','true');self.end_headers()
        def do_POST(self):
            if self.path!='/receipt' or self.headers.get('Origin')!=base or not secrets.compare_digest(self.headers.get('X-Task-Nonce',''),nonce):self.reply(403,b'{}');return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=8*1024*1024:raise ValueError('invalid size')
                receipt=json.loads(self.rfile.read(length))
                if receipt.get('type')!='task010-result' or (receipt.get('status')=='CAPTURED' and receipt.get('result',{}).get('fileReference')!=args.target_file):raise ValueError('invalid receipt context')
                name=f'discovery-{len(receipts)+1}.json'
                (output/name).write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode());receipts.append(name)
                self.reply(200,b'{"saved":true}')
            except (ValueError,TypeError,OSError):self.reply(400,b'{}')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    (output/'host-manifest.json').write_bytes((json.dumps({'baseUrl':base,'targetFile':args.target_file,'permissions':json.loads(served['/manifest.json'][1])['permissions']},indent=2)+'\n').encode())
    print(json.dumps({'manifestUrl':base+'/manifest.json','targetFile':args.target_file}),flush=True)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=='__main__':main()
