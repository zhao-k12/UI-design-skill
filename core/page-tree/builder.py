"""Build a semantic page tree, retaining source order and provenance."""
from __future__ import annotations

import copy
import hashlib
import json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def build(analysis):
    """Draft only; the independent structure gate decides whether it can freeze."""
    page = analysis['page']
    sections = []
    for block in page['blocks']:
        items = []
        for category in ('fields', 'buttons', 'dataRegions', 'staticContent'):
            for item in block[category]:
                items.append({'id': item['id'], 'kind': category,
                              'description': copy.deepcopy(item['description'])})
        sections.append({'id': block['id'], 'kind': 'Section',
                         'purpose': copy.deepcopy(block['purpose']), 'children': items})
    return {'version': '0.1.0', 'documentId': analysis['documentId'],
            'analysisSha256': fingerprint(analysis), 'stage': 'page-tree',
            'page': {'id': analysis['documentId'], 'kind': 'Page',
                     'identity': copy.deepcopy(page['identity']),
                     'primaryTask': copy.deepcopy(page['primaryTask']),
                     'children': sections}}
