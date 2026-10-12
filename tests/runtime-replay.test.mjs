import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, readFile, rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {compareRuns, replay} from '../scripts/runtime_replay.mjs';

async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), 'runtime-replay-'));
  const first = join(directory, 'first'), second = join(directory, 'second');
  for (const base of [first, second]) {
    await mkdir(base);
    const bundle = {status: 'PASS', components: [{componentType: 'Button', screenshot: {path: 'button.png'}}]};
    await writeFile(join(base, 'component_ir.json'), JSON.stringify(bundle));
    await writeFile(join(base, 'extraction_report.json'), JSON.stringify({status: 'PASS', sourceVersion: 'fixture-only'}));
    await writeFile(join(base, 'runtime_manifest.json'), '{"scope":"fixture-only"}');
    await writeFile(join(base, 'official-runtime-gallery.png'), 'fixture-gallery');
    await writeFile(join(base, 'button.png'), 'fixture-raster');
  }
  return {directory, first, second};
}

test('byte-identical retained runs compare without creating native acceptance', async () => {
  const f = await fixture();
  try {
    const report = await compareRuns(f.first, f.second);
    assert.equal(report.status, 'PASS');
    assert.equal(report.files.length, 5);
    assert.ok(report.files.every(r => r.equal));
  } finally {await rm(f.directory, {recursive: true, force: true});}
});

test('raw raster differences cannot be hidden by equal geometry or an extraction PASS', async () => {
  const f = await fixture();
  try {
    await writeFile(join(f.second, 'button.png'), 'changed-raster');
    const report = await compareRuns(f.first, f.second);
    assert.equal(report.status, 'FAIL');
    assert.ok(report.issues.some(i => i.code === 'runtime_bytes_not_repeatable' && i.path === 'button.png'));
    assert.equal(await readFile(join(f.first, 'button.png'), 'utf8'), 'fixture-raster');
  } finally {await rm(f.directory, {recursive: true, force: true});}
});

test('changed measurements and a failed extraction reject comparison', async () => {
  const f = await fixture();
  try {
    await writeFile(join(f.second, 'component_ir.json'), JSON.stringify({status: 'FAIL', components: []}));
    const report = await compareRuns(f.first, f.second);
    assert.equal(report.status, 'FAIL');
    assert.ok(report.issues.some(i => i.code === 'extraction_not_pass'));
    assert.ok(report.issues.some(i => i.code === 'component_ir_not_repeatable'));
  } finally {await rm(f.directory, {recursive: true, force: true});}
});

test('replay refuses output outside artifacts before executing the renderer', async () => {
  await assert.rejects(replay(join(tmpdir(), 'forbidden-runtime-output')), /artifacts child/);
});
