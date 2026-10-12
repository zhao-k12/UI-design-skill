import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,unlink,rmdir} from 'node:fs/promises';
import {join} from 'node:path';
import {probeFontFile} from '../component-builder/runtime-renderer/font-file-probe.mjs';
import {ROOT} from '../component-builder/source-reader/source-lock.mjs';
const identityPath=process.env.UI_DESIGN_FONT_IDENTITY ?? join(ROOT,'adapters/figma/metadata/font-file-identity.json');
test('actual hash-bound font reproduces official samples and restores source state',async()=>{
  const directory=await mkdtemp(join(ROOT,'artifacts/font-file-probe-test-'));
  const report=await probeFontFile(join(ROOT,'artifacts/task-006'),identityPath,directory);
  assert.equal(report.status,'PASS');assert.equal(report.ownerStatesRestored,true);assert.equal(report.temporaryFontFaceRemoved,true);
  assert.equal(report.referenceMatches.length,3);
  for(const row of report.observations) {
    assert.equal(row.ownerBoundsUnchanged,true);
    assert.deepEqual(await readFile(join(directory,row.pngPath)),await readFile(join(ROOT,'artifacts/task-006',row.logicalId+'.png')));
  }
  // Saved integration evidence remains in artifacts; it is never production admission.
  assert.equal(report.admissionEligible,false);
});
test('nonempty output is rejected before existing evidence is changed',async()=>{
  const directory=await mkdtemp(join(ROOT,'artifacts/font-file-probe-guard-'));const sentinel=join(directory,'sentinel');
  try {
    await writeFile(sentinel,'preserve');
    await assert.rejects(probeFontFile(join(ROOT,'artifacts/task-006'),identityPath,directory),/requires_new_output/);
    assert.equal(await readFile(sentinel,'utf8'),'preserve');
  } finally {await unlink(sentinel);await rmdir(directory);}
});
