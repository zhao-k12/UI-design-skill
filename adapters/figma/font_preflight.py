"""Source-font readiness for native candidates; never substitutes project fonts."""
from collections import defaultdict


def preflight_source_fonts(evidence, discovery, bindings=None):
    bindings = bindings or {}
    issues = []
    requirements = defaultdict(list)
    if evidence.get('scope') != 'official_runtime_font_diagnostic' or evidence.get('status') != 'PASS':
        issues.append({'code': 'invalid_source_font_evidence'})
    reference = evidence.get('referenceMatches', [])
    if not reference or any(item.get('screenshotMatches') is not True or item.get('environmentMatches') is not True for item in reference):
        issues.append({'code': 'font_reference_not_reproduced'})
    if discovery.get('scope') != 'figma_official_font_discovery' or not discovery.get('fileReference'):
        issues.append({'code': 'invalid_host_font_discovery'})
    if discovery.get('createdNodeIds') or discovery.get('mutatedNodeIds'):
        issues.append({'code': 'font_discovery_must_be_read_only'})
    for item in evidence.get('observations', []):
        for font in item.get('fonts', []):
            if font.get('glyphCount', 0) <= 0:
                continue
            family = font.get('familyName')
            if not isinstance(family, str) or not family:
                issues.append({'code': 'invalid_observed_font'})
                continue
            requirements[family].append({'logicalId': item.get('logicalId'), 'path': item.get('path'),
                'surface': item.get('surface'), 'postScriptName': font.get('postScriptName'),
                'isCustomFont': font.get('isCustomFont')})
    observed_ids = {item['logicalId'] for items in requirements.values() for item in items}
    for item in reference:
        if item.get('logicalId') not in observed_ids:
            issues.append({'code': 'component_font_usage_unknown', 'logicalId': item.get('logicalId')})
    rows = []
    for family, uses in sorted(requirements.items()):
        candidates = [font for font in discovery.get('matches', []) if font.get('family') == family]
        selected = bindings.get(family)
        status = 'MISSING'
        if family not in discovery.get('queriedFamilies', []):
            issues.append({'code': 'source_family_not_queried', 'family': family})
        elif not candidates:
            issues.append({'code': 'missing_official_font', 'family': family})
        elif selected is None:
            status = 'REQUIRES_EXPLICIT_STYLE_BINDING'
            issues.append({'code': 'source_font_style_unresolved', 'family': family})
        elif not isinstance(selected, dict) or selected.get('family') != family or selected not in candidates:
            status = 'INVALID_BINDING'
            issues.append({'code': 'official_font_substitution_forbidden', 'family': family})
        else:
            status = 'READY_FOR_LOAD'
        rows.append({'family': family, 'status': status, 'availableStyles': candidates,
            'binding': selected, 'uses': uses})
    if not requirements:
        issues.append({'code': 'no_observed_source_fonts'})
    return {'scope': 'figma_official_font_preflight', 'status': 'REVIEW' if issues else 'PASS',
        'fileReference': discovery.get('fileReference'), 'requirements': rows, 'issues': issues,
        'nativeExecution': 'NOT_RUN', 'fidelityGate': 'NOT_RUN', 'admissionEligible': False}
