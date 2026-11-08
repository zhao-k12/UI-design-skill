import json, hashlib, shutil
from pathlib import Path
from confirmed_modules import sidebar, topbar, breadcrumb, search_panel, table_panel, page_shell, action_column

task=Path('artifacts/measurement-records'); task.mkdir(parents=True, exist_ok=True)
src=Path(r'C:/Users/38442/AppData/Local/Temp/codex-clipboard-88dbbfae-51e9-45cd-b488-48f7eaf6d3b1.png')
dst=task/'prototype.png'; shutil.copy2(src,dst)
sha=hashlib.sha256(dst.read_bytes()).hexdigest()
menus=[
 {'name':'m1','label':'商机管理','icon':'home-line','children':[{'name':'m1-1','label':'售电商机'},{'name':'m1-2','label':'商机公海'}]},
 {'name':'m2','label':'商机管理','icon':'refresh-line'}, {'name':'m3','label':'商机公海','icon':'database-2-line'},
 {'name':'m4','label':'价值分析','icon':'apps-line'}, {'name':'m5','label':'绩效分析','icon':'pencil-line'},
 {'name':'m6','label':'电源端管理','icon':'flashlight-line'}, {'name':'m7','label':'渠道商管理','icon':'share-line','children':[{'name':'m7-1','label':'售电渠道'}]},
 {'name':'m8','label':'售电合同管理','icon':'file-list-3-line'}, {'name':'m9','label':'售后服务','icon':'customer-service-2-line'}, {'name':'m10','label':'测算管理','icon':'user-line'},
 {'name':'m11','label':'收益测算','icon':'user-line','children':[{'name':'m11-1','label':'测算模型'},{'name':'m11-2','label':'测算记录'},{'name':'m11-3','label':'采购成本'},{'name':'m11-4','label':'用户电量分析'},{'name':'m11-5','label':'佣金费率'},{'name':'m11-6','label':'其他成本'}]}
]
def bind_menu_sources(entries):
 for entry in entries:
  entry['sourceIds']=[entry['name']]
  bind_menu_sources(entry.get('children',[]))
bind_menu_sources(menus)
fields=[
 {'label':'测算编号','component':'Input','props':{'placeholder':'请输入'}},{'label':'关联商机编号','component':'Input','props':{'placeholder':'请输入'}},{'label':'客户名称','component':'Select','props':{'placeholder':'选择'}},{'label':'售电公司','component':'Select','props':{'placeholder':'选择'}},{'label':'创建时间','component':'DatePicker','props':{'type':'daterange','placeholder':'开始时间 - 结束时间'}},{'label':'创建人','component':'Input','props':{'placeholder':'请输入'}}]
cols=[{'title':x,'key':k} for x,k in [('测算编号','calc'),('客户名称','customer'),('售电公司','company'),('年用电量(kWh)','volume'),('度电毛利-通用(元/kWh)','margin1'),('度电毛利-临价(元/kWh)','margin2'),('预计签约时段','period'),('创建人','creator'),('创建时间','created')]]
action_col=action_column('results-actions',title='操作',key='actions'); action_col['cell']['children'][0]['template']['children'][0]['name']='eye-line'; cols.append(action_col)
rows=[]
for i in range(10):
 rows.append({'calc':'CAL202604010001','customer':'江苏星汉物业管理有限公司','company':'江苏苏鑫售电','volume':'13213.12','margin1':'0.012','margin2':'--' if i%2==0 else '0.123','period':'2026-06至2026-12','creator':'张三','created':'2026-07-20 14:30','actions':[{'label':'详情','icon':'eye-line','tone':''}]})
results=table_panel('results',cols,rows,table_source_ids=['table'],tabs=[{'name':'failed','label':'未通过'},{'name':'passed','label':'已通过'},{'name':'signed','label':'签约版'},{'name':'no-opp','label':'无商机测算'}],active_tab='no-opp',buttons=[{'label':'导出','icon':'download-line','primary':False}],page=True)
side=sidebar('side',menus,active_name='m11-2',open_names=['m11']); side['sourceIds']=[m['name'] for m in menus]+[c['name'] for m in menus for c in m.get('children',[])]
root=page_shell('page',sidebar_node=side,topbar_node=topbar('header'),breadcrumb_node=breadcrumb('crumb',['CRM系统','测算记录']),sections=[search_panel('query',fields),results])
def traits(leading='none',role='content'):
 return {'leading':leading,'trailing':'none','surface':'plain','shape':'rect','role':role}
items=[]
for m in menus:
 items.append({'id':m['name'],'region':'menu','decision':'include','treeRef':'side','traits':traits('icon:'+m['icon'],'menu'),'sourceEvidence':m['label']})
 for c in m.get('children',[]): items.append({'id':c['name'],'region':'menu','decision':'include','treeRef':'side','traits':traits('none','menu-item'),'sourceEvidence':c['label']})
items += [{'id':'table','region':'table','decision':'include','treeRef':'results-table','traits':traits('none','flat-table'),'sourceEvidence':'测算记录表格','tableColumns':[c['title'] for c in cols]}]
obs={'sourceSha256':sha,'items':items,'tableColumns':{'results-table':[c['title'] for c in cols]}}
scan={'sourceSha256':sha,'items':[dict(x,visual='独立复扫确认原型实例') for x in items],'tableColumns':{'results-table':[c['title'] for c in cols]}}
root['sourceSha256']=sha
root['icons']=['eye-line']
job={'title':'CRM测算记录','source':'prototype.png','viewport':{'width':1389,'height':832},'content':{'root':root,'sourceSha256':sha},'observation':obs,'scan':scan}
(task/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
print(task/'job.json')
