import {test} from 'node:test';
import assert from 'node:assert/strict';
import {probeBaselines} from '../component-builder/runtime-renderer/baseline-probe.mjs';
import {ROOT} from '../component-builder/source-reader/source-lock.mjs';
import {join} from 'node:path';

test('actual inline baseline instrumentation restores official geometry and screenshots',async()=>{
  const report=await probeBaselines(join(ROOT,'artifacts/test-baseline-probe'),join(ROOT,'artifacts/task-006'));
  assert.equal(report.status,'PASS');assert.equal(report.admissionEligible,false);
  const button=report.observations.find(row=>row.logicalId==='action.button.primary.medium');
  const select=report.observations.find(row=>row.logicalId==='form.select.default.medium');
  assert.equal(button.baselineComponentY,20.5);assert.equal(select.baselineComponentY,21);
  assert.ok(button.originalGeometryAndMarkupRestored&&select.originalGeometryAndMarkupRestored);
  const input=report.observations.find(row=>row.logicalId==='form.input.default.medium');
  assert.equal(input.status,'OBSERVED');assert.equal(input.baselineComponentY,21);
  assert.equal(input.surface,'user-agent-shadow');assert.ok(input.originalGeometryAndMarkupRestored);
  const arrow=report.observations.find(row=>row.surface==='pseudo:before');
  assert.equal(arrow.baselineComponentY,22);assert.ok(arrow.originalGeometryAndMarkupRestored);
});
test('baseline probe cannot overwrite the original official reference',async()=>{
  await assert.rejects(probeBaselines(join(ROOT,'artifacts/task-006'),join(ROOT,'artifacts/task-006')),/invalid_baseline_probe_output/);
});
