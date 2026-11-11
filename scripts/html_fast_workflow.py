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
from html_composition import compile_tree, save, digest, table_column_coverage
from audit_prototype_observations import audit
from html_compact import require_full_tree, delta_review, fingerprint, merge_patch

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
    # Starting a timer does not prove it coincided with the user request.
    value={'startedAt':now(),'scope':'timer-start; request start not verified','targetSeconds':300,'runs':[],'newTask':True,
           'tableColumnReviewPolicy':'flat-titled-v1', 'sourceEvidencePolicy':'complete-traits-v1', 'layoutQualityPolicy':'form-and-modules-v1'}
    save(timing,value);return value

def require_source_preflight(timing, root, observed, scanned):
    """Validate authored completeness and bindings, never semantic source truth."""
    if timing.get('sourceEvidencePolicy') != 'complete-traits-v1': return
    if not observed.get('items') or not scanned.get('items'):
        raise ValueError('source_observation_items_required_before_render')
    if {item.get('id') for item in observed.get('items', [])} != {item.get('id') for item in scanned.get('items', [])}:
        raise ValueError('independent_scan_item_coverage_mismatch_before_render')
    for item in observed.get('items', []):
        if item.get('decision') == 'include' and (not item.get('region') or not item.get('sourceEvidence') or not item.get('treeRef')):
            raise ValueError('source_include_requires_region_evidence_and_tree_binding:'+str(item.get('id')))
    for item in scanned.get('items', []):
        if item.get('decision') == 'include' and not item.get('visual'):
            raise ValueError('independent_scan_visual_evidence_required:'+str(item.get('id')))
    nodes={}
    def visit(node):
        nodes[node['id']]=node
        for child in node.get('children',[]): visit(child)
        for children in node.get('slots',{}).values():
            for child in children: visit(child)
        if 'template' in node: visit(node['template'])
        for col in node.get('props',{}).get('columns',[]):
            if isinstance(col,dict) and 'cell' in col: visit(col['cell'])
    visit(root)
    for document in (observed,scanned):
        for item in document.get('items',[]):
            traits=item.get('traits')
            if not isinstance(traits,dict) or any(not isinstance(traits.get(key),str) or not traits[key].strip() for key in ('leading','trailing','surface','shape','role')):
                raise ValueError('source_traits_incomplete:'+item['id'])
    included={item['id']:item for item in observed.get('items',[]) if item.get('decision')=='include'}
    for identifier,item in included.items():
        ref=item.get('treeRef')
        if ref not in nodes or identifier not in nodes[ref].get('sourceIds',[]):
            raise ValueError('source_binding_missing:'+identifier)
        leading=item['traits']['leading'].strip().lower()
        if leading in ('icon','图标') or leading.startswith(('icon:', 'icon ', '图标：', '图标:')) or leading.endswith(('-outline','-filled','-icon')):
            def has_icon(node):
                return bool(node.get('kind')=='icon' or node.get('icon') or node.get('props',{}).get('icon') or
                    any(has_icon(child) for child in node.get('children',[])) or
                    any(has_icon(child) for children in node.get('slots',{}).values() for child in children))
            if not has_icon(nodes[ref]):
                raise ValueError('source_icon_binding_missing:'+identifier)
    menu_sources={}
    def assign_menu_source(node,seen):
        for source_id in set(node.get('sourceIds',[])).intersection(included):
            if source_id in seen: continue
            seen.add(source_id)
            previous=menu_sources.get(source_id)
            if previous is None or assign_menu_source(previous,seen):
                menu_sources[source_id]=node
                return True
        return False
    for node in nodes.values():
        if node.get('component') in ('MenuItem','Submenu') and not set(node.get('sourceIds',[])).intersection(included):
            raise ValueError('menu_instance_source_missing:'+node['id'])
        if node.get('component') in ('MenuItem','Submenu') and not assign_menu_source(node,set()):
            raise ValueError('menu_instance_source_not_distinct:'+node['id'])

def require_flat_table_coverage(timing, root, observed, scanned):
    """Require source inventories for new flat, titled tables at publication.

    Old tasks lacking this policy retain compatibility. Untitled and grouped
    tables need a separate visual review and are deliberately not claimed by
    this simple column check.
    """
    if timing.get('tableColumnReviewPolicy') != 'flat-titled-v1':
        return
    nodes={}
    def visit(node):
        nodes[node['id']]=node
        for child in node.get('children',[]): visit(child)
        for children in node.get('slots',{}).values():
            for child in children: visit(child)
        if 'template' in node: visit(node['template'])
        if node.get('component')=='Table':
            for col in node.get('props',{}).get('columns',[]):
                if isinstance(col,dict) and 'cell' in col: visit(col['cell'])
    visit(root)
    eligible=set()
    for identifier,node in nodes.items():
        if node.get('kind')!='component' or node.get('component')!='Table': continue
        columns=node.get('props',{}).get('columns',[])
        if (isinstance(columns,list) and all(isinstance(col,dict) for col in columns)
            and not any('children' in col for col in columns)
            and any(isinstance(col.get('title'),str) and col['title'].strip() for col in columns)):
            eligible.add(identifier)
    coverage=table_column_coverage(nodes,observed,scanned)
    missing=sorted(eligible-set(coverage['checkedTables']))
    if missing: raise ValueError('flat_table_source_columns_unchecked:'+','.join(missing))

def complete_timing(timing, completed_at, rendered_at):
    """Finish an unverified timer; preserve legacy scope labels for readers."""
    timing['completedAt']=completed_at
    timing['elapsedSeconds']=(datetime.fromisoformat(completed_at)-datetime.fromisoformat(timing['startedAt'])).total_seconds()
    timing['reviewAndToolWaitSeconds']=(datetime.fromisoformat(completed_at)-datetime.fromisoformat(rendered_at)).total_seconds()
    # Older files labelled request-start also lacked verification.
    timing['scopeVerified']=False
    timing['elapsedMeaning']='lower bound from timer start; request start not verified'
    target=timing.get('targetSeconds',300)
    # A lower bound above the target proves failure; a shorter one cannot
    # establish success because work may have occurred before the timer.
    timing['targetMet']=False if timing['elapsedSeconds']>target else None
    return timing

def record_timing_event(task, event_name):
    """Record only an event explicitly reported by the caller, at call time."""
    if not isinstance(event_name,str) or not event_name.strip() or len(event_name.strip())>120:
        raise ValueError('timing_event_name_required')
    timing_path=task/'timing.json'
    if not timing_path.is_file():raise ValueError('timing_not_started')
    timing=read(timing_path)
    events=timing.setdefault('events',[])
    if not isinstance(events,list):raise ValueError('timing_events_invalid')
    event={'name':event_name.strip(),'at':now()}
    events.append(event);save(timing_path,timing)
    return event

def review_plan(observed, content, rendered):
    nodes={}
    def visit(value):
        # Only node positions count; business rows may legitimately have kind/id.
        nodes[value['id']]=value
        for child in value.get('children',[]):visit(child)
        for children in value.get('slots',{}).values():
            for child in children:visit(child)
        if 'template' in value:visit(value['template'])
        for column in value.get('props',{}).get('columns',[]):
            if 'cell' in column:visit(column['cell'])
    visit(content['root'])
    memberships=deepcopy(observed['_groupIds'])
    grouped={member for members in memberships.values() for member in members}
    for item in observed['items']:
        if item['id'] not in grouped:memberships['item:'+item['id']]=[item['id']]
    indexed={item['id']:item for item in observed['items']};groups={}
    for key,members in memberships.items():
        items=[indexed[member] for member in members];rules={};bindings=set()
        for item in items:
            bound=[n for n in nodes.values() if item['id'] in n.get('sourceIds',[])]
            if item.get('treeRef') in nodes:bound.append(nodes[item['treeRef']])
            bindings.update(n['id'] for n in bound)
            if item['decision']=='include':
                rules[item['id']]={'id':'rule:'+item['id'], 'component':'+'.join(sorted({n.get('component',n['kind']) for n in bound})),
                    'variantReason':'Reviewer confirms these bound nodes and their declared props against the original and current render.',
                    'officialEvidence':'node_modules/view-ui-plus/src/components/index.js; core/ui_ir.json',
                    'nodes':sorted({n['id'] for n in bound})}
        evidence={'items':items,'rules':rules,'bindings':sorted(bindings),'boundContent':{ref:nodes[ref] for ref in sorted(bindings)},
                  'render':{stage:{'geometry':data['geometrySha256'],'nodes':{ref:data['nodeSignatures'].get(ref) for ref in sorted(bindings)}} for stage,data in rendered['stages'].items()}}
        if any(item['decision']=='exclude' for item in items) or not bindings:
            evidence['wholeStageHashes']={stage:data['screenshotSha256'] for stage,data in rendered['stages'].items()}
        groups[key]={**evidence,'fingerprint':fingerprint(evidence)}
    return {'groups':groups,'reusableGroups':[], 'requiredStages':['tree','skeleton','component','delivery'],
            'layoutRelationIds':sorted({row['id'] for stage in rendered['stages'].values() for row in stage.get('layoutRelations',{}).get('results',[])}),
            'relations':observed.get('relations',[]),'meaning':'Expected facts only. Confirm after viewing source, contact sheet and detail originals.'}

def reusable_groups(previous, plan, rendered, source_hash):
    """Reuse only sealed visual confirmations with unchanged context and runtime."""
    if not previous:return []
    old=Path(previous['runDir'])
    try:
        receipt=read(old/'review-receipt.json');old_plan=read(old/'review-plan.json');qa=read(old/'html/qa.json')
        if receipt['sourceSha256']!=source_hash or receipt['planSha256']!=digest(old/'review-plan.json'):return []
        if receipt['reviewSha256']!=digest(old/'visual-review.json') or receipt['qaSha256']!=digest(old/'html/qa.json'):return []
        if any(digest(old/'html'/(stage+'.png'))!=qa['stages'][stage]['screenshotSha256'] for stage in ('skeleton','component','delivery')):return []
        runtime=('adapterSha256','exporterSha256','officialSourceSha256','officialCssSha256','snapshotSha256','relationCheckerSha256','moduleCssSha256','qualityCheckerSha256','assetHashes','iconHashes')
        if any(qa.get(key)!=rendered.get(key) for key in runtime):return []
        if read(old/'source-visual-qa.json').get('status')!='PASS':return []
        return [key for key,group in plan['groups'].items()
                if old_plan['groups'].get(key,{}).get('fingerprint')==group['fingerprint']
                and all(all(value is not None for value in stage['nodes'].values()) for stage in group['render'].values())]
    except (OSError,KeyError,ValueError):return []

def require_current_attempt(task, run_id):
    path=task/'latest-attempt.json'
    if not path.exists(): return  # Published legacy tasks have no attempt ledger.
    attempt=read(path)
    if attempt.get('status')!='ready' or attempt.get('runId')!=run_id:
        raise ValueError('latest_attempt_not_ready_or_current')

def _tree_nodes(node, out=None):
    out = {} if out is None else out
    if isinstance(node, dict):
        if isinstance(node.get('id'), str): out[node['id']] = node
        for child in node.get('children', []): _tree_nodes(child, out)
    return out

def _value_changes(before, after, prefix=''):
    if type(before) is not type(after): return [prefix or '*']
    if isinstance(before, dict):
        changes=[]
        for key in sorted(set(before)|set(after)):
            if key == 'children': continue
            path=f'{prefix}.{key}' if prefix else key
            if key not in before or key not in after: changes.append(path)
            else: changes.extend(_value_changes(before[key],after[key],path))
        return changes
    if isinstance(before, list): return [] if before==after else [prefix or '*']
    return [] if before==after else [prefix or '*']

def require_revision_scope(task, job):
    """Reject local revisions that change nodes or properties outside the declared scope."""
    scope=job.get('revisionScope')
    if not scope: return
    run_id=scope.get('baseRunId'); allowed=scope.get('allowedChanges')
    if not isinstance(run_id,str) or not isinstance(allowed,list) or not allowed:
        raise ValueError('revision_scope_invalid')
    base_path=task/'runs'/run_id/'job.json'
    if not base_path.is_file(): raise ValueError('revision_scope_base_run_missing')
    base=read(base_path)
    old_nodes=_tree_nodes(base.get('content',{}).get('root'))
    new_nodes=_tree_nodes(job.get('content',{}).get('root'))
    permission={item.get('nodeId'):set(item.get('paths',[])) for item in allowed
                if isinstance(item,dict) and isinstance(item.get('nodeId'),str) and isinstance(item.get('paths'),list)}
    violations=[]
    for node_id in sorted(set(old_nodes)|set(new_nodes)):
        if node_id not in old_nodes or node_id not in new_nodes:
            changes=['*']
        else:
            changes=_value_changes(old_nodes[node_id],new_nodes[node_id])
            old_children=[c.get('id') for c in old_nodes[node_id].get('children',[]) if isinstance(c,dict)]
            new_children=[c.get('id') for c in new_nodes[node_id].get('children',[]) if isinstance(c,dict)]
            if old_children!=new_children: changes.append('children')
        allowed_paths=permission.get(node_id,set())
        for path in changes:
            if not any(rule=='*' or path==rule or path.startswith(rule+'.') for rule in allowed_paths):
                violations.append(f'{node_id}:{path}')
    if violations: raise ValueError('revision_scope_violation:'+','.join(violations[:20]))

def render(job_path, task):
    task.mkdir(parents=True,exist_ok=True)
    run_id=uuid4().hex[:12]
    attempt={'runId':run_id,'input':str(job_path),'startedAt':now(),'status':'running'}
    save(task/'latest-attempt.json',attempt)
    try:
        _render(job_path,task,run_id)
    except Exception as exc:
        attempt.update(status='failed',finishedAt=now(),errorType=type(exc).__name__,error=str(exc))
        run=task/'runs'/run_id;run.mkdir(parents=True,exist_ok=True)
        if job_path.is_file():
            try: shutil.copyfile(job_path,run/'submitted-job.json')
            except OSError as snapshot_error: attempt['inputSnapshotError']=str(snapshot_error)
        save(run/'failure.json',attempt)
        save(task/'latest-attempt.json',attempt)
        raise
    attempt.update(status='ready',finishedAt=now())
    save(task/'latest-attempt.json',attempt)

def _render(job_path, task, run_id):
    if not (task/'timing.json').exists():
        start(task);timing=read(task/'timing.json');timing['scope']='render-start; analysis time not measured';save(task/'timing.json',timing)
    begin=time.perf_counter();job=read(job_path)
    require_revision_scope(task,job)
    timing=read(task/'timing.json')
    if timing.get('newTask') and (timing.get('sourceEvidencePolicy') != 'complete-traits-v1' or timing.get('tableColumnReviewPolicy') != 'flat-titled-v1' or timing.get('layoutQualityPolicy') != 'form-and-modules-v1'):
        raise ValueError('new_task_quality_policies_cannot_be_downgraded')
    source=(job_path.parent/job['source']).resolve();source_hash=digest(source)
    # Both independently authored scans must lock the same actual input.
    for part in ('content','observation','scan'):
        if job[part].get('sourceSha256')!=source_hash:raise ValueError('source_hash_mismatch')
    run=task/'runs'/run_id;run.mkdir(parents=True)
    save(run/'job.json',{**job,'source':str(source)})
    shutil.copyfile(source,run/('prototype'+source.suffix))
    first=expand_observations(job['observation']);second=expand_observations(job['scan'],scan=True)
    content=bind_groups(require_full_tree(job['content']),first['_groupIds'])
    require_source_preflight(timing,content['root'],first,second)
    if timing.get('layoutQualityPolicy'): content['layoutQualityPolicy']=timing['layoutQualityPolicy']
    save(run/'job.json',{**job,'source':str(source)})
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
    rendered=read(run/'html/qa.json');plan=review_plan(first,content,rendered)
    previous=read(task/'active-run.json') if (task/'active-run.json').exists() else None
    plan['reusableGroups']=reusable_groups(previous,plan,rendered,source_hash)
    plan['reuseFrom']=previous if plan['reusableGroups'] else None
    save(run/'review-plan.json',plan)
    active={'runId':run_id,'runDir':str(run),'source':str(source),'sourceSha256':source_hash,
            'pageSha256':digest(run/'html/page.html'),'planSha256':digest(run/'review-plan.json'),'renderedAt':now(),'reviewRequired':True}
    save(task/'active-run.json',active)
    timing=read(task/'timing.json');timing['runs'].append({'runId':run_id,'prepareSeconds':prepared-begin,'compileSeconds':compiled-prepared,'renderSeconds':finished-compiled,'machineSeconds':finished-begin})
    save(task/'timing.json',timing)
    print(json.dumps({'status':'REVIEW_REQUIRED',**active,'reviewSheet':str(run/'html/review-sheet.png'),'reusableGroups':plan['reusableGroups'],'screenshots':[str(run/'html'/(stage+'.png')) for stage in ('skeleton','component','delivery')]},ensure_ascii=False))

def finalize(review_path,task):
    active=read(task/'active-run.json');run=Path(active['runDir']);review=read(review_path)
    require_current_attempt(task,active['runId'])
    if review.get('runId')!=active['runId'] or review.get('sourceSha256')!=active['sourceSha256']:
        raise ValueError('review_not_bound_to_current_run')
    if digest(run/'html/page.html')!=active['pageSha256']:raise ValueError('render_changed_after_review')
    shots={stage:run/'html'/(stage+'.png') for stage in ('skeleton','component','delivery')}
    rendered=read(run/'html/qa.json')
    if read(task/'timing.json').get('layoutQualityPolicy'):
        responsive=rendered.get('responsiveQuality',{})
        if responsive.get('status')!='PASS' or not (run/'html/small-viewport.png').is_file() or digest(run/'html/small-viewport.png')!=responsive.get('screenshotSha256'):
            raise ValueError('responsive_quality_not_passed_or_changed')
    if rendered['status']!='PASS' or any(digest(path)!=rendered['stages'][stage]['screenshotSha256'] for stage,path in shots.items()):
        raise ValueError('render_or_screenshot_changed')
    if any(rendered['stages'][stage].get('layoutRelations',{}).get('status')!='PASS' for stage in shots):
        raise ValueError('layout_relations_not_checked_or_failed')
    if active.get('planSha256')!=digest(run/'review-plan.json'):raise ValueError('review_plan_changed')
    if digest(run/'html/review-sheet.png')!=rendered['reviewSheetSha256']:raise ValueError('review_sheet_changed')
    plan=read(run/'review-plan.json')
    if set(review.get('checkedLayoutRelations',[]))!=set(plan.get('layoutRelationIds',[])):
        raise ValueError('layout_relation_visual_confirmation_required')
    if plan['reusableGroups'] and not set(plan['reusableGroups']).issubset(reusable_groups(plan['reuseFrom'],plan,rendered,active['sourceSha256'])):
        raise ValueError('prior_review_evidence_changed')
    observed=read(run/'source-observations.json');scanned=read(run/'independent-scan.json')
    timing=read(task/'timing.json')
    if timing.get('tableColumnReviewPolicy') == 'flat-titled-v1':
        ir_path=run/'core/ui_ir.json'
        if digest(ir_path)!=rendered.get('uiIrSha256'): raise ValueError('rendered_tree_changed')
        require_flat_table_coverage(timing,read(ir_path)['root'],observed,scanned)
    expanded=expand_review(delta_review(review,plan),observed,shots)
    save(run/'visual-review.json',expanded)
    result=audit(Path(active['source']),observed,scanned,expanded,shots)
    save(run/'source-visual-qa.json',result)
    if result['status']!='PASS':raise ValueError('visual_review_failed:'+','.join(result['issues']))
    save(run/'review-receipt.json',{'sourceSha256':active['sourceSha256'],'planSha256':digest(run/'review-plan.json'),
         'reviewSha256':digest(run/'visual-review.json'),'qaSha256':digest(run/'html/qa.json')})
    delivery_name=read(run/'job.json').get('deliveryName')
    if not delivery_name or '/' in delivery_name or '\\' in delivery_name or not delivery_name.endswith('.html'):
        raise ValueError('delivery_name_must_be_breadcrumb_based_html_filename')
    shutil.copyfile(run/'html/page.html',task/delivery_name)
    shutil.copyfile(run/'html/page.html',task/'page.html')
    shutil.copyfile(run/'html/delivery.png',task/'delivery.png')
    timing=complete_timing(read(task/'timing.json'),now(),active['renderedAt'])
    save(task/'timing.json',timing)
    save(task/'delivery-receipt.json',{'status':'PASS','runId':active['runId'],'deliveryPage':str(task/delivery_name),'sourceSha256':active['sourceSha256'],
         'reviewInputSha256':digest(review_path),'pageSha256':digest(task/'page.html'),'timing':timing})
    print(json.dumps({'status':'PASS','page':str(task/'page.html'),'timing':timing},ensure_ascii=False))

def verify_delivery(task):
    """Check that the published page still matches a completed, reviewed run.

    This checks recorded evidence and hashes, not whether a human review was
    truthful, and cannot prevent files from being created outside this runner.
    """
    task=Path(task).resolve()
    try:
        receipt=read(task/'delivery-receipt.json')
        active=read(task/'active-run.json')
        require_current_attempt(task,active.get('runId'))
        if receipt.get('status')!='PASS' or receipt.get('runId')!=active.get('runId'):
            raise ValueError('delivery_run_not_finalized')
        run=Path(active['runDir']).resolve()
        if not run.is_relative_to(task/'runs') or run.name!=active['runId']:
            raise ValueError('delivery_run_path_invalid')
        for name in ('job.json','content-tree.json','source-observations.json','independent-scan.json','core/ui_ir.json'):
            if not (run/name).is_file(): raise ValueError('delivery_input_missing:'+name)
        sealed=read(run/'review-receipt.json')
        qa=read(run/'html/qa.json')
        if qa.get('responsiveQuality'):
            responsive=qa['responsiveQuality']
            if responsive.get('status')!='PASS' or digest(run/'html/small-viewport.png')!=responsive.get('screenshotSha256'):
                raise ValueError('delivery_responsive_evidence_changed')
        visual=read(run/'source-visual-qa.json')
        if qa.get('status')!='PASS' or visual.get('status')!='PASS':
            raise ValueError('delivery_checks_not_passed')
        if receipt.get('sourceSha256')!=active.get('sourceSha256') or sealed.get('sourceSha256')!=active.get('sourceSha256'):
            raise ValueError('delivery_source_mismatch')
        sources=list(run.glob('prototype.*'))
        if len(sources)!=1 or digest(sources[0])!=active['sourceSha256']:
            raise ValueError('delivery_source_changed')
        for key,path in (('planSha256',run/'review-plan.json'),('reviewSha256',run/'visual-review.json'),('qaSha256',run/'html/qa.json')):
            if sealed.get(key)!=digest(path): raise ValueError('delivery_evidence_changed:'+key)
        if active.get('planSha256')!=digest(run/'review-plan.json') or qa.get('uiIrSha256')!=digest(run/'core/ui_ir.json'):
            raise ValueError('delivery_tree_or_plan_changed')
        page_hash=digest(task/'page.html')
        if page_hash!=receipt.get('pageSha256') or page_hash!=active.get('pageSha256') or page_hash!=digest(run/'html/page.html'):
            raise ValueError('delivery_page_changed')
        for stage in ('skeleton','component','delivery'):
            if digest(run/'html'/(stage+'.png'))!=qa['stages'][stage]['screenshotSha256']:
                raise ValueError('delivery_screenshot_changed:'+stage)
        if digest(task/'delivery.png')!=qa['stages']['delivery']['screenshotSha256']:
            raise ValueError('published_screenshot_changed')
    except (OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError('delivery_evidence_missing_or_invalid') from exc
    return {'status':'PASS','page':str(task/'page.html'),'runId':active['runId'],
            'meaning':'Recorded evidence and hashes match; visual judgment is not automated.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['start','event','render','revise','finalize','verify'])
    parser.add_argument('--task-dir',type=Path,required=True);parser.add_argument('--input',type=Path)
    parser.add_argument('--event-name')
    args=parser.parse_args();task=args.task_dir.resolve()
    if not task.is_relative_to((ROOT/'artifacts').resolve()):parser.error('task_directory_must_be_in_artifacts')
    if args.mode=='start':start(task);print('Timing started; target 300 seconds, no timeout delivery shortcut.')
    elif args.mode=='verify':print(json.dumps(verify_delivery(task),ensure_ascii=False))
    elif args.mode=='event':
        if not args.event_name:parser.error('--event-name required')
        print(json.dumps(record_timing_event(task,args.event_name),ensure_ascii=False))
    else:
        if not args.input:parser.error('--input required')
        if args.mode=='render':render(args.input.resolve(),task)
        elif args.mode=='revise':
            active=read(task/'active-run.json');job=read(Path(active['runDir'])/'job.json')
            patched=merge_patch(job,read(args.input));path=task/'revised-job.json';save(path,patched);render(path,task)
        else:finalize(args.input.resolve(),task)

if __name__=='__main__':main()
