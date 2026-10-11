"""Extend the already authorized Table plugin with real instance acceptance."""
import json
import sys
from adapters.penpot.host import configurable_table_server as tables
from adapters.penpot.host import section_server as host
from validators.ui_ir import ROOT


def instance_assets(base,target_file,nonce,readback=None):
    served=tables.table_assets(base,target_file,nonce,readback)
    code=(ROOT/'adapters/penpot/configurable_table_instances.js').read_text(encoding='utf-8')
    plugin=served['/plugin.js'][1]+'\n'+code+'\nlet instanceExecution=null;\n'+'''
penpot.ui.onMessage(async message=>{
  if(!['instance-create','instance-read-0','instance-read-1'].includes(message?.type))return;
  try{
    if(penpot.currentFile.id!==targetFile)throw Error('instance_file_mismatch');
    const result=message.type==='instance-create'?await createTableLinkedInstances(penpot,tableExecution):await readTableLinkedInstance(penpot,instanceExecution,message.type.endsWith('0')?0:1);
    if(message.type==='instance-create')instanceExecution=result;
    penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
  }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
});'''
    served['/plugin.js']=('text/javascript',plugin)
    served['/index.html']=('text/html','''<!doctype html><meta charset="utf-8"><h3>TASK-019 真实实例验收</h3><p>仅在现有候选页制作两份关联实例，随后独立读取主组件和实例及完整原生 PNG。</p><button id="create-instances">创建两份真实实例</button><button id="read-first">独立读取两列实例</button><button id="read-second">独立读取四列实例</button><button id="inspect">读取实际环境</button><p id="status">等待执行</p><script src="client.js"></script>''')
    client=served['/client.js'][1]
    # Replace the obsolete candidate buttons, keeping original receipt transport.
    client=client[:client.index("\ndocument.getElementById('create').onclick")]
    for button,message in [('create-instances','instance-create'),('read-first','instance-read-0'),('read-second','instance-read-1')]:
        client+=f"\ndocument.getElementById('{button}').onclick=()=>parent.postMessage({{type:'{message}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    return served


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--source',action='append',required=True)
    args,remaining=parser.parse_known_args();tables.SOURCE_DIRECTORIES=[ROOT/source for source in args.source]
    sys.argv=[sys.argv[0],*remaining];host.section_assets=instance_assets;host.main()
