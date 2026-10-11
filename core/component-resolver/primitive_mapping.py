"""Explicit UI-IR Text primitive mapping, without creating a widget registry entry."""
import importlib

resolver=importlib.import_module('core.component-resolver.resolver')


def resolve(*args,allow_text_primitives=False,**kwargs):
    result=resolver.resolve(*args,**kwargs)
    if not allow_text_primitives or result['status']=='FAIL':return result
    decisions=args[5];registry=args[6]
    by_id={d['sourceId']:d for d in decisions['items']}
    for row in result['rows']:
        decision=by_id[row['sourceId']]
        if (row['intent']=='static' and row['status']=='Missing' and decision['confidence']=='high'
                and decision['preferredId'] is None and decision['variant'] is None):
            row.update(status='Resolved',componentType='Text',primitive='Text',reasonCode='source_text_primitive')
    if result['rows']:
        states={r['status'] for r in result['rows']}
        result['status']='Missing' if 'Missing' in states else 'Review' if 'Review' in states else 'PASS'
        result['readyForAssembly']=(result['status']=='PASS' and result['layoutReport']['readyForMapping']
                                    and not result['diagnosticOnly'] and registry.scope=='production')
    result['textPrimitivesEnabled']=True
    return result
