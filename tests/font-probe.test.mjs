import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ROOT } from '../component-builder/source-reader/source-lock.mjs';
import { extractRuntime } from '../component-builder/runtime-renderer/extract.mjs';
import { probeFonts } from '../component-builder/runtime-renderer/font-probe.mjs';

test('actual browser reports Chinese, placeholder and pseudo glyph fonts without changing reference pixels', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'font-probe-'));
  try {
    const reference = join(directory, 'reference');
    await extractRuntime(reference);
    const original = await readFile(join(reference, 'component_ir.json'));
    const report = await probeFonts(join(directory, 'probe'), reference);
    assert.equal(report.status, 'PASS');
    assert.equal(report.fidelityGate, 'NOT_RUN');
    assert.ok(report.referenceMatches.every(item => item.screenshotMatches && item.environmentMatches));
    assert.ok(report.observations.some(item => item.logicalId.startsWith('action.button') && item.fonts.some(font => font.glyphCount > 0)));
    assert.ok(report.observations.some(item => item.surface === 'user-agent-shadow' && item.fonts.some(font => font.glyphCount === 5)));
    assert.ok(report.observations.some(item => item.surface === 'pseudo:before' && item.fonts.some(font => font.isCustomFont && font.familyName === 'Ionicons')));
    assert.ok(report.observations.some(item => item.status === 'NO_GLYPHS_REPORTED'));
    assert.deepEqual(await readFile(join(reference, 'component_ir.json')), original);
    // Drift must become REVIEW; font discovery alone cannot assert reference equivalence.
    const changed = JSON.parse(original);
    changed.components[0].screenshot.sha256 = '0'.repeat(64);
    await writeFile(join(reference, 'component_ir.json'), JSON.stringify(changed));
    assert.equal((await probeFonts(join(directory, 'drift'), reference)).status, 'REVIEW');
    await assert.rejects(() => probeFonts(reference, reference), /reference_overwrite/);
    await writeFile(join(reference, 'component_ir.json'), JSON.stringify({ status: 'FAIL' }));
    await assert.rejects(() => probeFonts(join(directory, 'probe'), reference), /invalid_reference/);
    assert.equal(JSON.parse(await readFile(join(directory, 'probe/font_report.json'), 'utf8')).status, 'FAIL');
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('invalid observer and protected output are rejected', async () => {
  await assert.rejects(() => extractRuntime(join(ROOT, 'node_modules'), { observePage: true }), /invalid_runtime_observer/);
  await assert.rejects(() => probeFonts(join(ROOT, 'component-builder'), join(ROOT, 'artifacts/task-006')), /invalid_output_directory/);
});
