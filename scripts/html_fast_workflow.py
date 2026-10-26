"""One reusable entry for compact inputs, rendering, review expansion and timing."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core/pipeline'))
from html_composition import compile_tree, save, digest
from audit_prototype_observations import audit

def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def ids(group):
    if 'ids' in group: values=group['ids']
    else:
        count=group.get('count')
        if not isinstance(count,int) or isinstance(count,bool) or count<1: raise ValueError('group_count_required')
        values=[f"{group['prefix']}{i}" for i in range(group.get('start',0),group.get('start',0)+count)]
    if not values or len(set(values))!=len(values): raise ValueError('group_ids_invalid')
    return values

def expand_observations(document, scan=False):
    result=deepcopy(document); rows=result.setdefault('items',[]); groups={}
    for group in document.get('groups',[]):
        if group['id'] in groups: raise ValueError('duplicate_group_id')
        members=ids(group);groups[group['id']]=members
        common={key:deepcopy(group[key]) for key in ('region','traits','visual') if key in group}
        if not scan:
            common.update({key:deepcopy(group[key]) for key in ('sourceEvidence','treeRef','decision','reason') if key in group})
        for identifier in members:
            row=dict(common,id=identifier)
            row.update(deepcopy(group.get('exceptions',{}).get(identifier,{})))
            rows.append(row)
        if set(group.get('exceptions',{}))-set(members): raise ValueError('group_exception_unknown')
    if len({row['id'] for row in rows})!=len(rows): raise ValueError('duplicate_observation_id')
    for relation in result.setdefault('relations',[]):
        refs=relation.pop('sourceGroups',[])
        relation['sourceIds']=relation.get('sourceIds',[])+[member for ref in refs for member in groups[ref]]
    result['_groupIds']=groups
    return result

def bind_groups(value, groups):
    if isinstance(value,list): return [bind_groups(item,groups) for item in value]
    if not isinstance(value,dict): return value
    if set(value)=={'$repeat'}:
        spec=value['$repeat'];count=spec.get('count')
        if not isinstance(count,int) or isinstance(count,bool) or count<1:raise ValueError('data_repeat_count_required')
        exceptions=spec.get('exceptions',{})
        if any(not str(key).isdigit() or not 0<=int(key)<count for key in exceptions):raise ValueError('data_repeat_exception_unknown')
        result=[]
        for index in range(count):
            item=deepcopy(spec['value']);override=exceptions.get(str(index))
            if override is not None:
                if isinstance(item,dict) and isinstance(override,dict):item.update(override)
                else:item=deepcopy(override)
            result.append(bind_groups(item,groups))
        return result
    result={key:bind_groups(item,groups) for key,item in value.items() if key!='sourceGroups' or 'kind' not in value}
    if 'kind' in value and value.get('sourceGroups'):
        result['sourceIds']=result.get('sourceIds',[])+[member for group in value['sourceGroups'] for member in groups[group]]
    return result

def expand_review(document, observed, screenshots):
    result=deepcopy(document);rows=result.setdefault('items',[])
    for group in document.get('groups',[]):
        if group.get('status')!='PASS' or not group.get('renderedEvidence'):
            raise ValueError('group_visual_review_required')
        members=group.get('sourceIds',[])+[member for ref in group.get('sourceGroups',[]) for member in observed['_groupIds'][ref]]
        if not members: raise ValueError('review_group_empty')
        for member in members:
            item={'id':member,**{key:deepcopy(group[key]) for key in ('variantRef','renderedTraits','exclusionStatus') if key in group}}
            item.update(deepcopy(group.get('exceptions',{}).get(member,{})));rows.append(item)
        if set(group.get('exceptions',{}))-set(members):raise ValueError('review_exception_unknown')
    if len({row['id'] for row in rows})!=len(rows):raise ValueError('duplicate_review_id')
    result['screenshotSha256']={stage:digest(path) for stage,path in screenshots.items()}
    return result

def start(task):
    task.mkdir(parents=True,exist_ok=True)
    timing=task/'timing.json'
    if timing.exists():return read(timing)
    value={'startedAt':now(),'scope':'request-start','targetSeconds':300,'runs':[]}
    save(timing,value);return value

def render(job_path, task):
    if not (task/'timing.json').exists():
        start(task);timing=read(task/'timing.json');timing['scope']='render-start; analysis time not measured';save(task/'timing.json',timing)
    begin=time.perf_counter();job=read(job_path)
    source=(job_path.parent/job['source']).resolve();source_hash=digest(source)
    # Both independently authored scans must lock the same actual input.
    for part in ('content','observation','scan'):
        if job[part].get('sourceSha256')!=source_hash:raise ValueError('source_hash_mismatch')
    run_id=uuid4().hex[:12];run=task/'runs'/run_id;run.mkdir(parents=True)
    shutil.copyfile(source,run/('prototype'+source.suffix))
    first=expand_observations(job['observation']);second=expand_observations(job['scan'],scan=True)
    content=bind_groups(job['content'],first['_groupIds'])
    for name,value in (('content-tree',content),('source-observations',first),('independent-scan',second)):
        save(run/(name+'.json'),value)
    prepared=time.perf_counter();result=compile_tree(source,content,first,second)
    core=run/'core';core.mkdir()
    for name,value in result.items():save(core/(name+'.json'),value)
    result['qa_report']['uiIrSha256']=digest(core/'ui_ir.json');save(core/'qa_report.json',result['qa_report'])
    save(core/'manifest.json',{'sourceSha256':source_hash,'jobSha256':digest(job_path),'compilerSha256':digest(ROOT/'core/pipeline/html_composition.py'),'runnerSha256':digest(Path(__file__))})
    compiled=time.perf_counter();viewport=job.get('viewport',{})
    subprocess.run(['node',str(ROOT/'scripts/export_html_composition.mjs'),str(core),str(run/'html'),str(viewport.get('width',1440)),str(viewport.get('height',1000))],cwd=ROOT,check=True)
    finished=time.perf_counter()
    active={'runId':run_id,'runDir':str(run),'source':str(source),'sourceSha256':source_hash,
            'pageSha256':digest(run/'html/page.html'),'renderedAt':now(),'reviewRequired':True}
    save(task/'active-run.json',active)
    timing=read(task/'timing.json');timing['runs'].append({'runId':run_id,'prepareSeconds':prepared-begin,'compileSeconds':compiled-prepared,'renderSeconds':finished-compiled,'machineSeconds':finished-begin})
    save(task/'timing.json',timing)
    print(json.dumps({'status':'REVIEW_REQUIRED',**active,'screenshots':[str(run/'html'/(stage+'.png')) for stage in ('skeleton','component','delivery')]},ensure_ascii=False))

def finalize(review_path,task):
    active=read(task/'active-run.json');run=Path(active['runDir']);review=read(review_path)
    if review.get('runId')!=active['runId'] or review.get('sourceSha256')!=active['sourceSha256']:
        raise ValueError('review_not_bound_to_current_run')
    if digest(run/'html/page.html')!=active['pageSha256']:raise ValueError('render_changed_after_review')
    shots={stage:run/'html'/(stage+'.png') for stage in ('skeleton','component','delivery')}
    rendered=read(run/'html/qa.json')
    if rendered['status']!='PASS' or any(digest(path)!=rendered['stages'][stage]['screenshotSha256'] for stage,path in shots.items()):
        raise ValueError('render_or_screenshot_changed')
    observed=read(run/'source-observations.json');expanded=expand_review(review,observed,shots)
    save(run/'visual-review.json',expanded)
    result=audit(Path(active['source']),observed,read(run/'independent-scan.json'),expanded,shots)
    save(run/'source-visual-qa.json',result)
    if result['status']!='PASS':raise ValueError('visual_review_failed:'+','.join(result['issues']))
    shutil.copyfile(run/'html/page.html',task/'page.html')
    shutil.copyfile(run/'html/delivery.png',task/'delivery.png')
    timing=read(task/'timing.json');timing['completedAt']=now()
    timing['elapsedSeconds']=(datetime.fromisoformat(timing['completedAt'])-datetime.fromisoformat(timing['startedAt'])).total_seconds()
    timing['reviewAndToolWaitSeconds']=(datetime.fromisoformat(timing['completedAt'])-datetime.fromisoformat(active['renderedAt'])).total_seconds()
    timing['targetMet']=timing['elapsedSeconds']<=300 if timing['scope']=='request-start' else None
    save(task/'timing.json',timing)
    save(task/'delivery-receipt.json',{'status':'PASS','runId':active['runId'],'sourceSha256':active['sourceSha256'],
         'reviewInputSha256':digest(review_path),'pageSha256':digest(task/'page.html'),'timing':timing})
    print(json.dumps({'status':'PASS','page':str(task/'page.html'),'timing':timing},ensure_ascii=False))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['start','render','finalize'])
    parser.add_argument('--task-dir',type=Path,required=True);parser.add_argument('--input',type=Path)
    args=parser.parse_args();task=args.task_dir.resolve()
    if not task.is_relative_to((ROOT/'artifacts').resolve()):parser.error('task_directory_must_be_in_artifacts')
    if args.mode=='start':start(task);print('Timing started; target 300 seconds, no timeout delivery shortcut.')
    else:
        if not args.input:parser.error('--input required')
        if args.mode=='render':render(args.input.resolve(),task)
        else:finalize(args.input.resolve(),task)

if __name__=='__main__':main()
