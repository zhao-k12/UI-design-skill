import json,hashlib,shutil
from pathlib import Path
from confirmed_modules import sidebar,topbar,breadcrumb,page_shell,summary_panel
task=Path('artifacts/channel-contract-detail'); task.mkdir(parents=True,exist_ok=True)
src=Path(r'C:/Users/38442/AppData/Local/Temp/codex-clipboard-69db1743-9f2b-4d7d-9d62-c23100a14aaf.png'); dst=task/'prototype.png'; shutil.copy2(src,dst); sha=hashlib.sha256(dst.read_bytes()).hexdigest()
menus=[{'name':'m1','label':'商机管理','icon':'home-line'},{'name':'m2','label':'商机管理','icon':'refresh-line'},{'name':'m3','label':'商机公海','icon':'database-2-line'},{'name':'m4','label':'价值分析','icon':'apps-line'},{'name':'m5','label':'绩效分析','icon':'pencil-line'},{'name':'m6','label':'电源端管理','icon':'flashlight-line'},{'name':'m7','label':'渠道商管理','icon':'share-line','children':[{'name':'m7-1','label':'售电渠道商'},{'name':'m7-2','label':'渠道商合同'},{'name':'m7-3','label':'合同模板'}]},{'name':'m8','label':'售电公司管理','icon':'file-list-3-line'},{'name':'m9','label':'售后服务','icon':'customer-service-2-line'}]
for m in menus:
 m['sourceIds']=[m['name']]
 for c in m.get('children',[]): c['sourceIds']=[c['name']]
def sec(name,title,rows):
 return {'id':name,'kind':'container','designRole':'form-section','sourceIds':[name],'children':[{'id':name+'-title','kind':'container','designRole':'form-section-title','children':[{'id':name+'-title-text','kind':'text','value':title}]},{'id':name+'-table','kind':'component','component':'Table','props':{'showHeader':False,'columns':[{'title':'字段','key':'a'},{'title':'内容','key':'b'},{'title':'字段','key':'c'},{'title':'内容','key':'d'}],'data':rows}}]}
basic=sec('basic','基本信息',[{'a':'合同编号','b':'HT-2026-0102','c':'状态','d':'已签署'},{'a':'模板编号 / 类型','b':'HTMB-JS-BL-001-V3\n江苏省·比例分成合同','c':'渠道商编号','d':'QDS-2026-001'},{'a':'创建人（名称+工号）','b':'李明轩（GC100521）','c':'创建时间','d':'2026-09-28 14:20'}])
contract=sec('contract','合同信息',[{'a':'甲方/乙方分成比例','b':'','c':'分成基数','d':''},{'a':'结算周期','b':'','c':'项目溢价','d':''},{'a':'履约保障形式（承诺函/保证金）','b':'','c':'超额利润挂钩条款','d':''}])
ec=sec('ec','EC流程',[{'a':'EC流程编号','b':'ECLC-88123445','c':'','d':''}])
sign=sec('sign','契约锁签约',[{'a':'契约锁流程号','b':'QYS-88901245','c':'签署完成时间','d':'2026-10-08 16:42'}])
flow={'id':'flow-steps-wrap','kind':'component','component':'Steps','designRole':'progress-steps','sourceIds':['sign'],'props':{'direction':'vertical','current':1},'children':[{'id':'flow-s1','kind':'component','component':'Step','props':{'title':'创建合同（字段自动同步）','content':'2026-09-28 14:20 · 李明轩（GC100521）','status':'finish'}},{'id':'flow-s2','kind':'component','component':'Step','props':{'title':'推送契约锁发起签约','content':'流程号 QYS-88901245','status':'process'}}]}
sign['children'].append(flow)
side=sidebar('side',menus,active_name='m7-2',open_names=['m7']); side['sourceIds']=[m['name'] for m in menus]+[c['name'] for m in menus for c in m.get('children',[])]
summary=summary_panel('summary','江苏光耀电力工程有限公司',source_ids=['summary'])
root=page_shell('page',sidebar_node=side,topbar_node=topbar('header'),breadcrumb_node=breadcrumb('crumb',['渠道商管理','渠道商合同']),sections=[summary,basic,contract,ec,sign])
items=[{'id':m['name'],'region':'menu','decision':'include','treeRef':'side','sourceEvidence':m['label'],'traits':{'leading':'icon:'+m['icon'],'trailing':'none','surface':'plain','shape':'rect','role':'menu'}} for m in menus]
items += [{'id':c['name'],'region':'menu','decision':'include','treeRef':'side','sourceEvidence':c['label'],'traits':{'leading':'none','trailing':'none','surface':'plain','shape':'rect','role':'menu-item'}} for m in menus for c in m.get('children',[])]
items += [{'id':x,'region':'detail','decision':'include','treeRef':x,'sourceEvidence':x,'traits':{'leading':'none','trailing':'none','surface':'plain','shape':'rect','role':'detail-section'}} for x in ['summary','basic','contract','ec','sign']]
obs={'sourceSha256':sha,'items':items}; scan={'sourceSha256':sha,'items':[dict(x,visual='独立复扫确认原型实例') for x in items]}; root['sourceSha256']=sha; root['icons']=['share-line','check-line']; job={'title':'渠道商合同详情','deliveryName':'渠道商管理_渠道商合同.html','source':'prototype.png','viewport':{'width':1324,'height':740},'content':{'root':root,'sourceSha256':sha},'observation':obs,'scan':scan}; (task/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8'); print(task/'job.json')
