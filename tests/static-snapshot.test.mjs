import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { staticSnapshot, inspectStaticDelivery } from '../adapters/html/static-snapshot.mjs';

test('delivery snapshot keeps visible state and text but cannot hover or run scripts', async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><head><style>button{background:blue}button:hover{background:red}.selected{font-weight:bold}</style></head><body><div id="app"><nav class="stage-nav">review</nav><button class="selected" onclick="window.clicked=true">商品类型</button><input value="原型内容"></div><script>window.runtime=true</script></body></html>');
    const frozen = await staticSnapshot(page);
    assert.match(frozen, /商品类型/);
    assert.match(frozen, /value="原型内容"/);
    assert.doesNotMatch(frozen, /<script|stage-nav|onclick=/);
    await page.setContent(frozen);
    const result = await inspectStaticDelivery(page);
    assert.equal(result.scripts, 0);
    assert.equal(result.reviewControls, 0);
    assert.equal(result.buttonPointerEvents, 'none');
    assert.equal(result.buttonTabIndex, -1);
    const button = page.locator('button');
    const before = await button.evaluate(node => getComputedStyle(node).backgroundColor);
    const box = await button.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    const after = await button.evaluate(node => getComputedStyle(node).backgroundColor);
    assert.equal(after, before);
    assert.equal(await button.evaluate(node => getComputedStyle(node).fontWeight), '700');
  } finally {
    await browser.close();
  }
});
