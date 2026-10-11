import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ROOT, LOCK_PATH, jsonFile, verifySource, hash } from '../component-builder/source-reader/source-lock.mjs';
import { extractRuntime } from '../component-builder/runtime-renderer/extract.mjs';

test('source lock detects changed source identities and files without modifying official files', async () => {
  const lock = await verifySource();
  assert.equal(lock.packageVersion, '1.3.24');
  const changed = structuredClone(lock);
  changed.files['node_modules/view-ui-plus/dist/styles/viewuiplus.css'] = '0'.repeat(64);
  changed.filesSha256 = hash(JSON.stringify(changed.files));
  await assert.rejects(() => verifySource(changed), /source_lock_mismatch/);
  const identity = structuredClone(lock);
  identity.sourceVersion = 'other';
  await assert.rejects(() => verifySource(identity), /invalid_source_lock/);
});

test('official browser runtime extracts three real components repeatedly with matching styles and pixels', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'ui-runtime-test-'));
  try {
    const first = await extractRuntime(join(directory, 'first'));
    const second = await extractRuntime(join(directory, 'second'));
    assert.deepEqual(first.result, second.result);
    assert.deepEqual(first.report, second.report);
    assert.deepEqual(first.report.componentTypes, ['Button', 'Input', 'Select']);
    assert.equal(first.report.fidelityGate, 'NOT_RUN');
    for (const component of first.result.components) {
      assert.ok(component.rootBounds.width > 0 && component.rootBounds.height > 0);
      assert.ok(component.nodes[0].attributes.class.includes('ivu-'));
      assert.equal(component.resolvedProps.size, 'default');
      assert.equal(hash(await readFile(join(directory, 'first', component.screenshot.path))), component.screenshot.sha256);
      assert.equal(component.provenance.sourceLockSha256, hash(await readFile(LOCK_PATH)));
    }
    const input = first.result.components.find(component => component.componentType === 'Input');
    assert.ok(input.nodes.some(node => node.tag === 'input' && node.attributes.placeholder === '请输入姓名' && node.pseudoElements['::placeholder']));
    const select = first.result.components.find(component => component.componentType === 'Select');
    assert.ok(select.nodes.some(node => node.visible && node.textRuns.some(run => run.text === '启用')));
    assert.ok(select.iconMetrics.some(icon => icon.visible && icon.pseudoElements['::before']));
    assert.equal((await jsonFile(join(directory, 'first/runtime_manifest.json'))).source.repository, 'https://github.com/view-design/ViewUIPlus');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('output directory cannot overwrite source packages', async () => {
  await assert.rejects(() => extractRuntime(join(ROOT, 'node_modules')), /invalid_output_directory/);
});
