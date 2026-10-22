"""Version-locked static pipeline; pure Core stages, with resumable byte-bound artifacts."""
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
from jsonschema.exceptions import ValidationError

from core.prototype.parser import parse
from core.layout.builder import generate, RULES
from validators.structure.gate import check, builder
from validators.ui_ir import validate_document, load_json, ROOT

mapping_module=import_module('core.component-resolver.primitive_mapping')
assembly_module=import_module('core.component-resolver.assembly')
materialize_module=import_module('core.component-resolver.materialize')
resources_module=import_module('core.asset-resolver.resolver')
resolver_module=import_module('core.component-resolver.resolver')

VERSION_KEYS=('skill_version','ui_ir_version','component_library_version','component_source_version',
              'remix_icon_version','design_token_version','design_rule_version','figma_adapter_version','penpot_adapter_version')


class Blocked(Exception):
    def __init__(self, stage, record):self.stage,self.record=stage,record


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def run(observations, source_root, review, layout_plan, decisions, content, components, tokens,
        icons, assets, geometry, icon_sources, versions, output_dir, *, previous_assembly=None,
        measurement_evidence=None, evidence_root=None, delivery_mode='native'):
    """A resource PASS is never a native or final visual PASS; host evidence is separate."""
    output=Path(output_dir).resolve();source_root=Path(source_root).resolve()
    if not set(VERSION_KEYS)<=set(versions) or any(not isinstance(versions[k],str) or not versions[k] for k in VERSION_KEYS):
        raise ValueError('All frozen pipeline versions are required')
    if versions['skill_version']!=(ROOT/'VERSION').read_text(encoding='utf-8').strip():
        raise ValueError('Skill version differs from the installed release')
    if versions['component_library_version']!=components.snapshot['libraryVersion'] or versions['component_source_version']!=components.snapshot['sourceVersion'] or versions['design_token_version']!=tokens.version:
        raise ValueError('Current registries differ from declared versions')
    if versions['ui_ir_version']!='0.1.0' or versions['design_rule_version']!=RULES['version'] or versions['remix_icon_version']!=icons.snapshot['sourceVersion']:
        raise ValueError('Current contract, rules or icon source differ from declared versions')
    if components.scope!='production':raise ValueError('Production pipeline requires admitted production components')
    if delivery_mode not in ('native', 'html-official-runtime'):
        raise ValueError('Unknown delivery mode')
    source_files=[(source_root/s['path']).resolve() for s in observations['sources']]
    if output==source_root or any(p.is_relative_to(output) for p in source_files):raise ValueError('Pipeline output cannot contain or overwrite prototype inputs')
    output.mkdir(parents=True,exist_ok=True)
    lock={'version':'0.1.0','versions':deepcopy(versions),'registries':{'components':components.fingerprint,'tokens':tokens.fingerprint,
          'icons':icons.fingerprint,'assets':assets.fingerprint,'sourceGeometry':geometry.fingerprint},'rulesSha256':builder.fingerprint(RULES)}
    if delivery_mode != 'native':lock['deliveryMode']=delivery_mode
    programs=[p for directory in ('core','schemas','validators') for p in (ROOT/directory).rglob('*')
              if p.is_file() and p.suffix in ('.py','.json')]
    # Python/JSON contracts use repository LF text. Normalize only CRLF line
    # endings so a Windows checkout and the committed text lock identically.
    lock['programSha256']=builder.fingerprint({p.relative_to(ROOT).as_posix():sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sorted(programs)})
    manifest=output/'manifest.json'
    if manifest.exists() and load_json(manifest)!=lock:raise ValueError('Version migration requires a new task directory')
    if not manifest.exists():write(manifest,lock)
    checkpoint_path=output/'checkpoint.json';checkpoint=load_json(checkpoint_path) if checkpoint_path.exists() else {'version':'0.1.0','manifestSha256':builder.fingerprint(lock),'stages':{}}
    if checkpoint.get('manifestSha256')!=builder.fingerprint(lock):raise ValueError('Checkpoint belongs to another version lock')
    stages=checkpoint['stages'];executed=[];reused=[];ordered=[];invalidated=False
    code_hash=sha256(Path(__file__).read_bytes()).hexdigest()
    current_sources={}
    def stage(name, inputs, callback, filename, accepted=('PASS',)):
        nonlocal invalidated
        ordered.append(name);fingerprint=builder.fingerprint({'inputs':inputs,'program':code_hash,'manifest':lock})
        path=output/filename;prior=stages.get(name)
        if not invalidated and prior and prior.get('inputSha256')==fingerprint and path.is_file() and sha256(path.read_bytes()).hexdigest()==prior.get('artifactSha256'):
            value=load_json(path);reused.append(name)
        else:
            invalidated=True;value=callback();write(path,value);executed.append(name)
        if value.get('status') not in accepted:
            stages.pop(name,None);raise Blocked(name,value)
        stages[name]={'inputSha256':fingerprint,'artifact':filename,'artifactSha256':sha256(path.read_bytes()).hexdigest(),'status':value['status']}
        write(checkpoint_path,checkpoint)
        return value
    try:
        for source,path in zip(observations['sources'],source_files):
            if not path.is_relative_to(source_root):raise ValueError('Prototype source escapes its declared root')
            current_sources[source['path']]=sha256(path.read_bytes()).hexdigest()
        if any(m['source']['kind']=='runtime' for m in layout_plan['measurements'].values()):
            if measurement_evidence is None or evidence_root is None:raise ValueError('Production layout needs bound runtime measurement evidence')
            base=Path(evidence_root).resolve();path=(base/measurement_evidence['sourceCapture']).resolve()
            if not path.is_relative_to(base) or sha256(path.read_bytes()).hexdigest()!=measurement_evidence['sourceCaptureSha256']:
                raise ValueError('Runtime measurement capture changed or escaped its root')
            rows=load_json(path)['evidence'];metrics={n['uiIrId']:n for n in rows}
            if len(metrics)!=len(rows):raise ValueError('Ambiguous runtime source measurements')
            for identifier,measurement in layout_plan['measurements'].items():
                evidence=measurement_evidence['measurements'][identifier];nodes=[metrics[i] for i in evidence['uiIrIds']]
                if evidence['widthRule'] not in ('max','sum-with-spacing.sm') or evidence['heightRule'] not in ('sum','max'):
                    raise ValueError('Unknown measurement composition rule')
                width=max(n['width'] for n in nodes) if evidence['widthRule']=='max' else sum(n['width'] for n in nodes)+tokens.resolve('spacing.sm')
                height=sum(n['height'] for n in nodes) if evidence['heightRule']=='sum' else max(n['height'] for n in nodes)
                if (width,height)!=(measurement['width'],measurement['height']) or measurement['source']['reference']!='metrics.'+identifier:
                    raise ValueError('Layout size is not its declared runtime measurement')
            for item in content['items']:
                if 'textSize' in item:
                    uid=measurement_evidence['textMeasurements'][item['sourceId']];node=metrics[uid]
                    if item['textSize']!={k:node[k] for k in ('width','height')} or item['props']['text']['text']!=node['characters']:
                        raise ValueError('Text measurement differs from runtime source')
                for children in item.get('cellSlots',{}).values():
                    for child in children:
                        if child['type']=='Text':
                            node=metrics[measurement_evidence['slotMeasurements'][child['id']]]
                            if child['text']!=node['characters'] or any(child['layout'][a]['value']!=node[a] for a in ('width','height')):
                                raise ValueError('Slot text size differs from runtime source')
        parsed=stage('semantic-parse',{'observations':observations,'sourceBytes':current_sources},lambda:{'status':'SOURCE_VERIFIED','analysis':parse(observations,source_root)},'semantic_stage.json',('SOURCE_VERIFIED',))
        analysis=parsed['analysis'];write(output/'prototype_analysis.json',analysis)
        tree_stage=stage('page-tree',analysis,lambda:{'status':'PASS','tree':builder.build(analysis)},'page_tree_stage.json')
        page_tree=tree_stage['tree'];write(output/'page_tree.json',page_tree)
        structure=stage('structure-qa',{'analysis':analysis,'tree':page_tree,'review':review,'sources':current_sources},lambda:check(analysis,page_tree,source_root,review),'structure_qa_report.json')
        def layout():
            tree,report=generate(analysis,page_tree,source_root,review,layout_plan,tokens)
            if report['status']=='PASS':
                repeated,again=generate(analysis,page_tree,source_root,review,layout_plan,tokens)
                if tree!=repeated or report!=again:raise ValueError('Layout generation is not repeatable')
            return {'status':report['status'],'tree':tree,'report':report}
        layout_stage=stage('layout',{'structure':structure,'plan':layout_plan,'measurementEvidence':measurement_evidence},layout,'layout_stage.json')
        layout_tree=layout_stage['tree'];write(output/'layout_tree.json',layout_tree);write(output/'layout_qa_report.json',layout_stage['report'])
        mapped=stage('component-mapping',{'layout':layout_stage,'decisions':decisions},lambda:mapping_module.resolve(analysis,page_tree,source_root,review,layout_plan,decisions,components,tokens,allow_text_primitives=True),'component_mapping.json')
        by_content={item['sourceId']:item for item in content['items']};evidence={e['id']:e for e in analysis['evidence']}
        for row in mapped['rows']:
            if row['componentType']=='Table':
                source=geometry.source_component(row['componentId'],row['variant']);records=by_content[row['sourceId']].get('tableRecords')
                if records is None:raise ValueError('Table needs explicit source-bound static records')
                plain=[]
                for record in records:
                    values={}
                    for key,claim in record.items():
                        if not set(claim['evidence']).intersection(row['evidence']) or not any(claim['text'] in evidence[ref]['quote'] for ref in claim['evidence']):
                            raise ValueError('Table records lack original prototype evidence')
                        values[key]=claim['text']
                    plain.append(values)
                if delivery_mode == 'native' and plain!=source['resolvedProps']['data']:
                    raise Blocked('component-mapping',{'status':'Unsupported','issues':['Table record override is not admitted; source Body cannot be silently substituted']})
        # Annotation is diagnostic and carries the same current mapping fingerprint.
        (output/'component_annotation.html').write_text(resolver_module.annotation(mapped),encoding='utf-8',newline='\n')
        baseline=previous_assembly
        prior=stages.get('component-assembly');prior_path=output/'assembly.json'
        if baseline is None and prior and prior_path.is_file() and sha256(prior_path.read_bytes()).hexdigest()==prior.get('artifactSha256'):
            candidate=load_json(prior_path)
            if candidate.get('status')=='PASS' and candidate.get('pageTreeSha256')==builder.fingerprint(page_tree) and candidate.get('skeletonSha256')==builder.fingerprint(mapped['layoutReport']['engineReport']['skeleton']):
                baseline=candidate
        assembled=stage('component-assembly',{'mapping':mapped,'content':content,'icons':{k:sha256(v).hexdigest() for k,v in icon_sources.items()},'explicitPrevious':previous_assembly,'deliveryMode':delivery_mode},lambda:assembly_module.assemble(analysis,page_tree,source_root,review,layout_plan,decisions,components,tokens,content,previous=baseline,icon_registry=icons,icon_sources=icon_sources,source_geometry=geometry,allow_text_primitives=True,content_mode=delivery_mode),'assembly.json')
        if not assembled['readyForAdapter']:raise Blocked('component-assembly',{'status':'Review','issues':['Assembly has no production readiness']})
        materialized=stage('content-injection',{'assembly':assembled,'layout':layout_tree},lambda:materialize_module.materialize(assembled,layout_tree,tokens,document_id=observations['documentId']),'materialized.json')
        resources=stage('resource-resolution',materialized,lambda:resources_module.resolve(materialized['document'],assets,components=components,icons=icons),'resource_report.json')
        def rules():
            document=deepcopy(resources['document'])
            # Project region colors come from the locked token registry; component
            # instance appearance remains the admitted official source truth.
            for page in document['pages']:
                page['style']={'fill':{'token':'color.page'}}
                for section in page['children']:
                    section['style']={'fill':{'token':'color.surface'}}
            issues=validate_document(document)+resolver_module.tokens.check_references(document,tokens)
            return {'status':'FAIL' if issues else 'PASS','issues':issues,'document':document}
        design=stage('design-rules',resources,rules,'design_rule_report.json')
        document=design['document']
        semantic_ids={i['id'] for s in page_tree['page']['children'] for i in s['children']};covered=set();instances=[];icon_ids=[];texts=[]
        def walk(node):
            covered.update(node.get('sourceIds',[]))
            if node['type']=='Text':texts.append(node['text'])
            if node['type']=='ComponentInstance':
                instances.append(node['componentId'])
                scope=components.inspect(node['componentId']).get('contentScope') or {}
                if scope.get('kind')=='fixed-native-snapshot':
                    texts.extend(scope.get('visibleText',[]))
            if node['type']=='IconInstance':icon_ids.append(node['iconId'])
            for child in node.get('children',[]):walk(child)
            for children in node.get('slots',{}).values():
                for child in children:walk(child)
        for page in document['pages']:walk(page)
        issues=[]
        if not semantic_ids<=covered:issues.append('Missing semantic source items')
        for item in content['items']:
            for claim in item['props'].get('headers',[]):
                if claim['text'] not in texts:issues.append('Missing table header: '+claim['text'])
        for item in content['items']:
            if 'text' in item['props'] and item['props']['text']['text'] not in texts:issues.append('Missing static source content')
        if issues:raise Blocked('completeness-qa',{'status':'FAIL','issues':issues})
        qa={'scope':'static-core-pipeline','status':'PASS','readyForAdapter':True,'nativeExecution':'NOT_RUN','finalVisualQa':'NOT_RUN','v01Ready':False,
            'semanticItemCount':len(semantic_ids),'instanceCount':len(instances),'iconCount':len(icon_ids),'layoutRepeatable':True,'issues':[],
            'uiIrSha256':builder.fingerprint(document),'manifestSha256':builder.fingerprint(lock),'executedStages':executed,'reusedStages':reused}
        write(output/'final_ui_ir.json',document);write(output/'qa_report.json',qa);return qa
    except (Blocked,ValueError,KeyError,TypeError,OSError,ValidationError) as exc:
        blocked=exc if isinstance(exc,Blocked) else Blocked(ordered[-1] if ordered else 'inputs',{'status':'FAIL','issues':[str(exc)]})
        active=set(ordered[:-1]);checkpoint['stages']={k:v for k,v in stages.items() if k in active};write(checkpoint_path,checkpoint)
        qa={'scope':'static-core-pipeline','status':blocked.record.get('status','FAIL'),'blockedStage':blocked.stage,'readyForAdapter':False,
            'nativeExecution':'NOT_RUN','v01Ready':False,'issues':blocked.record.get('issues',[]),'executedStages':executed,'reusedStages':reused}
        write(output/'final_ui_ir.json',None);write(output/'qa_report.json',qa);return qa
