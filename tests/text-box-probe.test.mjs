import {test} from 'node:test';
import assert from 'node:assert/strict';
import {decodeShadowTextBoxes,probeTextBoxes} from '../component-builder/runtime-renderer/text-box-probe.mjs';
import {ROOT} from '../component-builder/source-reader/source-lock.mjs';
import {join} from 'node:path';

test('actual browser shadow and pseudo text boxes preserve locked references',async()=>{
  const report=await probeTextBoxes(join(ROOT,'artifacts/test-text-box-probe'),join(ROOT,'artifacts/task-006'));
  assert.equal(report.status,'PASS');assert.equal(report.admissionEligible,false);
  const placeholder=report.observations.find(row=>row.surface==='user-agent-shadow'&&row.text==='请输入姓名');
  assert.deepEqual(placeholder.componentBounds,{x:8,y:8,width:70,height:16});
  const arrow=report.observations.find(row=>row.text==='\uf116');
  assert.deepEqual(arrow.componentBounds,{x:217,y:9,width:14,height:14});
  const metric=report.canvasMetrics.find(row=>row.text==='请输入姓名');
  assert.equal(metric.surface,'::placeholder');assert.equal(metric.metrics.width,70);
  assert.ok(Number.isFinite(metric.metrics.actualBoundingBoxAscent));
  assert.ok(!report.canvasMetrics.some(row=>row.text==='无匹配数据'));
  const style=report.renderingSettings.find(row=>row.logicalId==='action.button.primary.medium').rows.find(row=>row.path==='0.0'&&row.surface==='element').properties;
  assert.equal(style['text-decoration-line'],'none');assert.equal(style['text-shadow'],'none');
  assert.equal(style['mix-blend-mode'],'normal');assert.equal(style.opacity,'1');
});
test('shadow decoder rejects invalid measured geometry',()=>{
  const snapshot={domNodes:[{attributes:[{name:'data-runtime-case',value:'fixture'}],childNodeIndexes:[1]},{shadowRootType:'user-agent'}],layoutTreeNodes:[{domNodeIndex:1,layoutText:'a',inlineTextNodes:[{boundingBox:{x:NaN,y:0,width:1,height:1},startCharacterIndex:0,numCharacters:1}]}]};
  assert.throws(()=>decodeShadowTextBoxes(snapshot),/invalid_shadow_text_box/);
});
test('output cannot replace the official reference',async()=>{
  await assert.rejects(probeTextBoxes(join(ROOT,'artifacts/task-006'),join(ROOT,'artifacts/task-006')),/invalid_text_probe_output/);
});
