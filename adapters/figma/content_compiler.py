"""Declared content extension of the frozen TASK-009 compiler."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from importlib import import_module

from adapters.figma.compiler import prepare as prepare_layout
from validators.ui_ir import load_json, validate_document

ROOT=Path(__file__).resolve().parents[2]
TEXT_TARGETS={'action.button.primary.medium':('label','查询'),
              'form.input.default.medium':('placeholder','source/placeholder'),
              'form.select.default.medium':('value','source/selected-value-text')}


def prepare(document,tokens,components,bindings,icons,icon_bindings=None,font_bindings=None,*,file_reference=None):
    issues=validate_document(document)
    result={'status':'FAIL','scope':'figma-content-adapter-preflight','nativeExecution':'NOT_RUN','issues':issues,'plan':None}
    if issues:return result
    declarations=load_json(ROOT/'adapters/figma/metadata/content-bindings.json')
    if declarations['registrySha256']!=components.fingerprint:
        result['issues'].append({'code':'content_registry_migration_required'});return result
    stripped=deepcopy(document);content={}
    def walk(node):
        if node['type']=='ComponentInstance' and (node.get('props') or node.get('slots')):
            logical=node['componentId'];mode,name=TEXT_TARGETS.get(logical,(None,None))
            if not mode:raise ValueError('No declared source text mapping for '+logical)
            props=node.get('props',{});slots=node.get('slots',{})
            if mode=='label':
                if props or set(slots)!={'label'} or len(slots['label'])!=1:raise ValueError('Only one Button text label is declared')
                text_node=slots['label'][0]
                if text_node.get('type')!='Text' or set(text_node)-{'id','type','text','sourceIds'}:raise ValueError('Styled or nested source labels are unsupported')
                text=text_node['text']
            else:
                if slots or set(props)!={mode}:raise ValueError('Only the admitted '+mode+' state is declared')
                text=props[mode]
            if not isinstance(text,str) or not text or '\n' in text or '\r' in text:raise ValueError('Nonempty single-line source text is required')
            declaration=declarations['components'][logical]
            reference=bindings.resolve(logical,node.get('variant'))
            if declaration['componentReference']!=reference['componentReference'] or declaration['fileReference']!=file_reference:raise ValueError('Content source binding mismatch')
            path=(ROOT/declaration['capturePath']).resolve()
            if not path.is_relative_to((ROOT/'adapters/figma/metadata').resolve()) or sha256(path.read_bytes()).hexdigest()!=declaration['captureSha256']:raise ValueError('Content source evidence changed')
            evidence=load_json(path)
            if evidence['rootReference']!=reference['componentReference']:raise ValueError('Content source master reference mismatch')
            found=[n for n in evidence['nodes'] if n.get('type')=='TEXT' and n.get('name')==name]
            if len(found)!=1:raise ValueError('Source text mapping must be unique')
            properties=found[0]['properties'];fields=('fontName','fontSize','lineHeight','letterSpacing','textAutoResize','textAlignHorizontal','textAlignVertical')
            if not all(k in properties for k in fields):raise ValueError('Incomplete source text style')
            content[node['id']]=[dict(name=name,originalText=properties['characters'],text=text,style={k:deepcopy(properties[k]) for k in fields})]
            node.pop('props',None);node.pop('slots',None)
        for child in node.get('children',[]):walk(child)
    try:
        for page in stripped['pages']:walk(page)
        baseline=prepare_layout(stripped,tokens,components,bindings,icons,icon_bindings,font_bindings,file_reference=file_reference)
        if baseline['status']!='PASS':return baseline
        def attach(node):
            if node['id'] in content:node['nativeContent']=content[node['id']]
            for child in node.get('children',[]):attach(child)
        plan=baseline['plan']
        for page in plan['pages']:attach(page)
        plan['adapterVersion']='0.1.1-content'
        plan['uiIrSha256']=import_module('validators.structure.gate').builder.fingerprint(document)
        result.update(status='PASS',plan=plan)
    except (ValueError,KeyError,TypeError) as exc:result['issues'].append({'code':'unsupported_component_content','detail':str(exc)})
    return result
