import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { readFile } from 'node:fs/promises';
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

test('uploaded values have explicit row states and hover only when requested', async () => {
  const css=await readFile(new URL('../adapters/html/confirmed-modules.css',import.meta.url),'utf8');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage();
    await page.setContent(`<!doctype html><html><head><style>${css}.remix-delete-bin-line{display:inline-block}</style></head><body><div id="app"><table><tbody>
      <tr><td><div data-design-role="uploaded-value" data-preview-state="default"><span>默认</span><i class="remix-delete-bin-line"></i></div></td></tr>
      <tr><td><div data-design-role="uploaded-value" data-preview-state="hover"><span>展示</span><i class="remix-delete-bin-line"></i></div></td></tr>
      <tr><td><div data-design-role="uploaded-value" data-preview-state="default" data-hover-preview="true"><span>经过</span><i class="remix-delete-bin-line"></i></div></td></tr>
      </tbody></table><input placeholder="静态"></div></body></html>`);
    await page.setContent(await staticSnapshot(page));
    const cells=page.locator('[data-design-role="uploaded-value"]');
    const visibility=i=>cells.nth(i).locator('i').evaluate(e=>getComputedStyle(e).visibility);
    assert.deepEqual(await Promise.all([visibility(0),visibility(1),visibility(2)]),['hidden','visible','hidden']);
    const first=await cells.nth(0).boundingBox();await page.mouse.move(first.x+first.width/2,first.y+first.height/2);
    assert.equal(await visibility(0),'hidden');
    await cells.nth(2).hover();assert.equal(await visibility(2),'visible');
    await page.mouse.move(0,0);assert.equal(await visibility(2),'hidden');
    assert.equal(await page.locator('input').evaluate(e=>getComputedStyle(e).pointerEvents),'none');
    assert.equal(await page.locator('input').evaluate(e=>e.tabIndex),-1);
  } finally {await browser.close()}
});

test('fixed table snapshot shares horizontal scroll and fills wide containers', async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 500, height: 400 } });
    await page.setContent(`<!doctype html><html><head><style>
      .ivu-table-wrapper{width:100%}.ivu-table{position:relative}.ivu-table-body{overflow-x:auto}
      .ivu-table-fixed-right{position:absolute;right:0;top:0;width:100px}
      .ivu-table-hidden{visibility:hidden}table{table-layout:fixed}
      </style></head><body><div id="app"><div class="ivu-table-wrapper"><div class="ivu-table">
      <div class="ivu-table-header"><table style="width:800px"><tr><th>标题</th><th class="ivu-table-hidden">操作</th></tr></table></div>
      <div class="ivu-table-body"><table style="width:800px"><tr><td>内容</td><td class="ivu-table-hidden">详情</td></tr></table></div>
      <div class="ivu-table-fixed-right">操作</div></div></div></div></body></html>`);
    await page.setContent(await staticSnapshot(page));
    const read = () => page.evaluate(() => {
      const body = document.querySelector('.ivu-table-body');
      return { overflow: body.scrollWidth - body.clientWidth,
        headerWidth: body.querySelector('.ivu-table-header table').getBoundingClientRect().width,
        tableWidth: body.querySelector(':scope > table').getBoundingClientRect().width,
        overlay: getComputedStyle(document.querySelector('.ivu-table-fixed-right')).display,
        action: getComputedStyle(body.querySelector('td:last-child')).visibility };
    });
    let narrow = await read();
    assert.ok(narrow.overflow > 0);
    assert.equal(narrow.headerWidth, narrow.tableWidth);
    assert.notEqual(narrow.overlay, 'none');
    await page.setViewportSize({ width: 1000, height: 400 });
    const wide = await read();
    assert.equal(wide.overflow, 0);
    assert.equal(wide.headerWidth, wide.tableWidth);
    assert.equal(wide.overlay, 'none');
    assert.equal(wide.action, 'visible');
  } finally { await browser.close(); }
});
