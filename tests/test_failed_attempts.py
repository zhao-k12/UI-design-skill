import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from html_fast_workflow import render, require_current_attempt


def test_malformed_input_preserves_raw_bytes_and_blocks_previous_run(tmp_path):
    task=tmp_path/'task';job=tmp_path/'bad.json';job.write_bytes(b'{invalid input')
    with pytest.raises(json.JSONDecodeError): render(job,task)
    attempt=json.loads((task/'latest-attempt.json').read_text())
    assert attempt['status']=='failed'
    run=task/'runs'/attempt['runId']
    assert (run/'submitted-job.json').read_bytes()==job.read_bytes()
    assert json.loads((run/'failure.json').read_text())['errorType']=='JSONDecodeError'
    with pytest.raises(ValueError,match='latest_attempt_not_ready_or_current'):
        require_current_attempt(task,'previous-success')


def test_legacy_and_ready_attempts(tmp_path):
    require_current_attempt(tmp_path,'legacy')
    (tmp_path/'latest-attempt.json').write_text(json.dumps({'status':'ready','runId':'current'}))
    require_current_attempt(tmp_path,'current')
    with pytest.raises(ValueError,match='latest_attempt_not_ready_or_current'):
        require_current_attempt(tmp_path,'stale')
