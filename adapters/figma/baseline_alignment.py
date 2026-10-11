"""Compare measured DOM baselines with actual native SVG/font coordinate evidence."""
import math
import re
from adapters.figma.font_outline_comparison import compare_font_files


def compare_baseline_alignment(source,native,font_identity,component_inventory):
    if source.get('scope')!='official_runtime_baseline_diagnostic' or source.get('status')!='PASS' or not source.get('referenceMatches') or any(row.get('screenshotMatches') is not True or row.get('environmentMatches') is not True for row in source['referenceMatches']):raise ValueError('baseline_reference_not_reproduced')
    if native.get('createdNodeIds') or native.get('mutatedNodeIds') or native.get('admissionEligible') is not False:raise ValueError('native_baseline_capture_not_readonly')
    comparison=compare_font_files(native,font_identity)
    reference_hash=source.get('referenceComponentIrSha256')
    if not isinstance(reference_hash,str) or not re.fullmatch('[0-9a-f]{64}',reference_hash) or reference_hash!=font_identity.get('referenceComponentIrSha256'):raise ValueError('baseline_reference_identity_mismatch')
    shapes={row['textReference']:row for row in comparison['observations']}
    component_ids={row['logicalId']:row['componentReference'] for row in component_inventory['components']}
    matched=source['referenceMatches']
    if len(matched)!=len(component_ids) or {row.get('logicalId') for row in matched}!=set(component_ids):raise ValueError('baseline_component_inventory_mismatch')
    if native['fileReference']!=component_inventory['fileReference']:raise ValueError('baseline_file_mismatch')
    contexts={row['textReference']:row for row in native['coordinateContext']}
    observations=[]
    for source_row in source['observations']:
        logical_id=source_row['logicalId'];surface=source_row.get('surface','element')
        if logical_id not in component_ids:raise ValueError('baseline_unknown_component')
        if source_row['status']!='OBSERVED':
            observations.append({'logicalId':logical_id,'surface':surface,'status':'UNSUPPORTED'});continue
        if not source_row.get('originalGeometryAndMarkupRestored'):raise ValueError('baseline_probe_not_restored')
        if isinstance(source_row.get('baselineComponentY'),bool) or not isinstance(source_row.get('baselineComponentY'),(int,float)) or not math.isfinite(source_row['baselineComponentY']):raise ValueError('invalid_source_baseline_value')
        component=component_ids.get(logical_id)
        candidates=[row for row in native['observations'] if contexts[row['textReference']]['componentReference']==component and
            ((surface=='pseudo:before' and row['fontName']['family']=='Ionicons') or (surface!='pseudo:before' and row['fontName']['family']!='Ionicons'))]
        if len(candidates)!=1:raise ValueError('baseline_text_role_unresolved')
        text=candidates[0];context=contexts[text['textReference']];shape=shapes[text['textReference']]
        if source_row.get('characters') is not None and source_row['characters']!=text.get('characters'):raise ValueError('baseline_text_content_mismatch')
        for key in ('textAbsoluteTransform','componentAbsoluteTransform'):
            matrix=context[key]
            if not isinstance(matrix,list) or len(matrix)!=2 or any(not isinstance(row,list) or len(row)!=3 or any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) for value in row) for row in matrix):raise ValueError('invalid_baseline_transform')
            if [matrix[0][:2],matrix[1][:2]]!=[[1,0],[0,1]]:raise ValueError('baseline_transform_unsupported')
        source_ink=shape['source']['unshapedInkBoundsBaselineCoordinates'];svg=shape['nativeSvg']['pathBoundsSvgCoordinates']
        if not shape['dimensionEqual']:raise ValueError('baseline_font_ink_dimensions_differ')
        offset=svg['y']-source_ink['y']
        baseline=context['textAbsoluteTransform'][1][2]-context['componentAbsoluteTransform'][1][2]+offset
        observations.append({'logicalId':logical_id,'surface':surface,'textReference':text['textReference'],
            'sourceBaselineComponentY':source_row['baselineComponentY'],'nativeFontBaselineComponentY':baseline,
            'deltaY':baseline-source_row['baselineComponentY'],'positionStatus':'ALIGNED' if baseline==source_row['baselineComponentY'] else 'DIFFERENCE',
            'nativeSvgBaselineOffset':offset,'exactContourCoordinatesEqual':shape['contourComparison']['unorientedGeometry']['exactCoordinatesEqual']})
    return {'scope':'figma_complete_baseline_alignment_diagnostic','status':'REVIEW','observations':observations,
        'admissionEligible':False,'fidelityGate':'NOT_RUN','limitations':['Baseline coordinates use actual source markers and native SVG/font ink extents with identity linear transforms.',
            'Ink dimension/position agreement does not establish fill winding, hinting, served font equivalence or exact pixel equality.']}
