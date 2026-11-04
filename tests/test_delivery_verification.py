import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from html_fast_workflow import digest, verify_delivery


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def sealed_task(task):
    run = task / 'runs' / 'run1'
    (run / 'html').mkdir(parents=True)
    (run / 'core').mkdir()
    (run / 'prototype.png').write_bytes(b'source')
    for name in ('job.json', 'content-tree.json', 'source-observations.json', 'independent-scan.json', 'core/ui_ir.json', 'review-plan.json', 'visual-review.json'):
        write(run / name, {})
    for stage in ('skeleton', 'component', 'delivery'):
        (run / 'html' / (stage + '.png')).write_bytes(stage.encode())
    (run / 'html/page.html').write_text('page', encoding='utf-8')
    (task / 'page.html').write_text('page', encoding='utf-8')
    (task / 'delivery.png').write_bytes(b'delivery')
    source_hash = digest(run / 'prototype.png')
    page_hash = digest(task / 'page.html')
    qa = {'status': 'PASS', 'uiIrSha256': digest(run / 'core/ui_ir.json'),
          'stages': {s: {'screenshotSha256': digest(run / 'html' / (s + '.png'))} for s in ('skeleton', 'component', 'delivery')}}
    write(run / 'html/qa.json', qa)
    write(run / 'source-visual-qa.json', {'status': 'PASS'})
    write(run / 'review-receipt.json', {'sourceSha256': source_hash, 'planSha256': digest(run / 'review-plan.json'),
          'reviewSha256': digest(run / 'visual-review.json'), 'qaSha256': digest(run / 'html/qa.json')})
    write(task / 'active-run.json', {'runId': 'run1', 'runDir': str(run), 'sourceSha256': source_hash,
          'pageSha256': page_hash, 'planSha256': digest(run / 'review-plan.json')})
    write(task / 'delivery-receipt.json', {'status': 'PASS', 'runId': 'run1', 'sourceSha256': source_hash, 'pageSha256': page_hash})
    return run


def test_rejects_directly_written_page(tmp_path):
    (tmp_path / 'page.html').write_text('handwritten', encoding='utf-8')
    with pytest.raises(ValueError, match='delivery_evidence_missing_or_invalid'):
        verify_delivery(tmp_path)


def test_sealed_page_and_tampering(tmp_path):
    run = sealed_task(tmp_path)
    assert verify_delivery(tmp_path)['status'] == 'PASS'
    (tmp_path / 'page.html').write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='delivery_page_changed'):
        verify_delivery(tmp_path)
    (tmp_path / 'page.html').write_text('page', encoding='utf-8')
    (run / 'core/ui_ir.json').write_text('{"changed":true}', encoding='utf-8')
    with pytest.raises(ValueError, match='delivery_tree_or_plan_changed'):
        verify_delivery(tmp_path)
