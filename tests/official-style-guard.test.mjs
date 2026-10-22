import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { assertNoOfficialComponentOverrides } from '../adapters/html/official-style-guard.mjs';

test('page layout hosts and skeleton annotations are allowed', () => {
  assert.doesNotThrow(() => assertNoOfficialComponentOverrides('.content{display:grid}.skeleton-cell{color:blue}'));
});

test('local CSS cannot restyle an official component, even under a page wrapper', () => {
  assert.throws(() => assertNoOfficialComponentOverrides('.table-wrap .ivu-table td{height:52px}'),
    /official_component_style_override/);
});

test('historical customer-page CSS is rejected before export', async () => {
  const localCss = await readFile(new URL('../adapters/html/prototype-layout.css', import.meta.url), 'utf8');
  assert.throws(() => assertNoOfficialComponentOverrides(localCss), /official_component_style_override/);
});
