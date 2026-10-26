"""Batch composition execution and expand compact evidence without inventing reviews."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'core/pipeline'),str(ROOT/'scripts')]
from html_composition import compile_tree, save
from audit_prototype_observations import audit

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return sha256(path.read_bytes()).hexdigest()

def expand(value):
    """Expand independently authored repeated observations into stable item IDs."""
    result={key:item for key,item in value.items() if key!='groups'}
    result['items']=list(value.get('items',[]))
    for group in value.get('groups',[]):
        count=group['count']
        if not isinstance(count,int) or isinstance(count,bool) or count<1:raise ValueError('group_count_invalid')
        for i in range(count):
            item={key:part for key,part in group.items() if key not in ('count','overrides')}
            item={key:part.format(i=i,n=i+1) if isinstance(part,str) else part for key,part in item.items()}
            item.update(group.get('overrides',{}).get(str(i),{}))
            result['items'].append(item)
    ids=[item['id'] for item in result['items']]
    if len(ids)!=len(set(ids)):raise ValueError('expanded_id_duplicate')
    return result

def review_draft(observation,screenshots):
    groups={}
    for item in observation['items']:
        if item['decision']!='include':continue
        key=json.dumps(item['traits'],sort_keys=True,ensure_ascii=False)
        groups.setdefault(key,[]).append(item)
    return {'sourceSha256':observation['sourceSha256'],'reviewMode':'batched-v2',
        'screenshotSha256':{key:digest(path) for key,path in screenshots.items()},
        'stageChecks':{stage:'PENDING' for stage in ('tree','skeleton','component','delivery')},
        'groups':[{'id':'variant-'+str(i),'sourceIds':[item['id'] for item in items],
                   'expectedSourceTraits':items[0]['traits'],'renderedTraits':None,
                   'component':'','variantReason':'','officialEvidence':'','status':'PENDING'}
                  for i,items in enumerate(groups.values())],
        'excludedIdsReviewed':[],
        'relationChecks':[{'id':rel['id'],'status':'PENDING','officialEvidence':'','renderedEvidence':''}
                          for rel in observation.get('relations',[])]}

def expand_review(observation,decisions):
    included={item['id'] for item in observation['items'] if item['decision']=='include'}
    excluded={item['id'] for item in observation['items'] if item['decision']=='exclude'}
    results={};rules=[]
    for group in decisions['groups']:
        if group.get('status')!='PASS' or not isinstance(group.get('renderedTraits'),dict):
            raise ValueError('visual_group_not_reviewed:'+group['id'])
        if not group.get('component') or not group.get('variantReason') or not group.get('officialEvidence'):
            raise ValueError('visual_evidence_missing:'+group['id'])
        rules.append({key:group[key] for key in ('id','component','variantReason','officialEvidence')})
        for key in group['sourceIds']:
            if key in results or key not in included:raise ValueError('review_group_coverage_invalid:'+key)
            results[key]={'id':key,'variantRef':group['id'],'renderedTraits':group['renderedTraits']}
    if set(results)!=included or set(decisions.get('excludedIdsReviewed',[]))!=excluded:
        raise ValueError('review_coverage_incomplete')
    return {key:decisions[key] for key in ('sourceSha256','reviewMode','screenshotSha256','stageChecks','relationChecks')}|{
        'variantRules':rules,'items':list(results.values())+[{'id':key,'exclusionStatus':'PASS'} for key in sorted(excluded)]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['build','finalize'])
    p.add_argument('task',type=Path)
    p.add_argument('--revision',default='r1')
    p.add_argument('--width',type=int,default=1440);p.add_argument('--height',type=int,default=1000)
    args=p.parse_args();task=args.task.resolve()
    if not task.is_relative_to((ROOT/'artifacts').resolve()):p.error('task_must_be_in_artifacts')
    out=task/args.revision;out.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();timings={}
    source=task/'prototype.png'
    observation=expand(read(task/'source-observations.json'))
    scan=expand(read(task/'independent-scan.json'))
    screenshots={stage:out/'html'/(stage+'.png') for stage in ('skeleton','component','delivery')}
    if args.mode=='build':
        core=out/'core'
        if (core/'manifest.json').exists():p.error('revision_exists_choose_new_revision')
        stamp=time.perf_counter()
        result=compile_tree(source,read(task/'content-tree.json'),observation,scan)
        core.mkdir(parents=True,exist_ok=True)
        for name,value in result.items():save(core/(name+'.json'),value)
        result['qa_report']['uiIrSha256']=digest(core/'ui_ir.json');save(core/'qa_report.json',result['qa_report'])
        save(core/'manifest.json',{'sourceSha256':digest(source),'contentSha256':digest(task/'content-tree.json'),
            'compilerSha256':digest(ROOT/'core/pipeline/html_composition.py'),
            'workflowSha256':digest(Path(__file__)),'officialSourceSha256':result['ui_ir']['officialSource']['sourceSha256']})
        save(out/'source-observations.json',observation);save(out/'independent-scan.json',scan)
        timings['compileSeconds']=time.perf_counter()-stamp;stamp=time.perf_counter()
        subprocess.run(['node',str(ROOT/'scripts/export_html_composition.mjs'),str(core),str(out/'html'),str(args.width),str(args.height)],cwd=ROOT,check=True)
        timings['renderSeconds']=time.perf_counter()-stamp
        save(out/'review-decisions.json',review_draft(observation,screenshots))
        timings.update(toolSeconds=time.perf_counter()-start,status='AWAITING_VISUAL_REVIEW',
                       measurementScope='Tool execution only; excludes model understanding, input writing and screenshot review.')
        save(out/'timing.json',timings)
        print(json.dumps({'status':timings['status'],'toolSeconds':timings['toolSeconds'],'review':str(out/'review-decisions.json')}))
    else:
        # Use the exact build observations. Do not finalize new input against old images.
        if read(out/'source-observations.json')!=observation or read(out/'independent-scan.json')!=scan:
            p.error('source_evidence_changed_rebuild_required')
        manifest=read(out/'core/manifest.json')
        if digest(source)!=manifest['sourceSha256'] or digest(task/'content-tree.json')!=manifest['contentSha256']:
            p.error('input_changed_rebuild_required')
        review=expand_review(observation,read(out/'review-decisions.json'))
        result=audit(source,observation,scan,review,screenshots)
        save(out/'visual-review.json',review);save(out/'source-visual-qa.json',result)
        if result['status']!='PASS':p.exit(1,json.dumps(result,ensure_ascii=False)+'\n')
        print(json.dumps({'status':'PASS','page':str(out/'html/page.html')},ensure_ascii=False))

if __name__=='__main__':main()
