// Build one audited HTML page from a reviewed screenshot content tree.
import { build } from 'esbuild';
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import { resolve, join, dirname, extname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT, verifySource } from '../component-builder/source-reader/source-lock.mjs';
import { assertNoOfficialComponentOverrides } from '../adapters/html/official-style-guard.mjs';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const arg = name => { const at = process.argv.indexOf(name); return at < 0 ? undefined : process.argv[at + 1]; };
const icons = [
  'focus-2-line', 'home-4-line', 'file-list-3-line', 'user-3-line',
  'inbox-archive-line', 'bank-card-line', 'bar-chart-2-line',
  'customer-service-2-line', 'mail-open-line', 'team-line', 'computer-line',
  'menu-fold-line', 'search-line', 'volume-up-line', 'lock-line',
  'settings-3-line', 'account-circle-line', 'arrow-down-s-line',
  'restart-line', 'filter-3-line', 'add-line', 'flag-line',
  'file-add-line', 'repeat-line', 'download-2-line', 'upload-2-line',
  'refresh-line', 'edit-2-line', 'checkbox-circle-line', 'delete-bin-line',
  'radio-button-line', 'add-circle-line', 'phone-line', 'chat-3-line',
];

async function officialCss() {
  const source = join(ROOT, 'node_modules/view-ui-plus/dist/styles/viewuiplus.css');
  let css = await readFile(source, 'utf8');
  for (const [, , raw] of [...css.matchAll(/url\((['"]?)([^)'"\s]+)\1\)/g)]) {
    if (/^(data:|https?:|#)/i.test(raw)) continue;
    const file = resolve(dirname(source), raw.split(/[?#]/)[0]);
    assert(file.startsWith(join(ROOT, 'node_modules/view-ui-plus/dist')), 'CSS asset outside locked official package');
    const bytes = await readFile(file);
    const mime = { '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.svg': 'image/svg+xml', '.png': 'image/png' }[extname(file)] ?? 'application/octet-stream';
    css = css.replaceAll(raw, `data:${mime};base64,${bytes.toString('base64')}`);
  }
  return css;
}

function html(payload, css, js) {
  const json = JSON.stringify(payload).replaceAll('<', '\\u003c');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>客户管理</title><style>${css}</style></head><body><div id="app"></div><script type="application/json" id="design-payload">${json}</script><script type="module">${js.replaceAll('</script', '<\\/script')}</script></body></html>`;
}

async function inspect(page, stage, tree) {
  await page.evaluate(value => window.__setDesignStage(value), stage);
  return page.evaluate(({ stage, tree }) => {
    const root = document.querySelector('.design-page');
    const card = document.querySelector('.content-card');
    const table = document.querySelector('.ivu-table');
    const tableWrap = document.querySelector('.table-wrap');
    const box = element => {
      const rect = element?.getBoundingClientRect();
      return rect ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height } : null;
    };
    const content = root?.innerText ?? '';
    const names = stage === 'delivery' ? [tree.title, tree.brand, ...tree.navigation,
      ...tree.breadcrumb, ...tree.filterActions, ...tree.toolbarActions,
      ...tree.table.columns.slice(1), ...Object.values(tree.table.repeatedRow).filter(value => typeof value === 'string'),
      ...tree.table.repeatedRow.actions, tree.floating.demo, ...tree.floating.shortcuts] : [];
    const fields = stage === 'delivery' ? [tree.topbar.searchPlaceholder,
      ...tree.filters.map(filter => filter.placeholder)] : [];
    const inputs = [...document.querySelectorAll('input')].map(input => `${input.placeholder} ${input.value}`)
      .concat([...document.querySelectorAll('.ivu-select-placeholder')].map(node => node.textContent ?? ''));
    return { stage, page: box(root), card: box(card), table: box(table), tableWrap: box(tableWrap),
      skeletonBlockCount: document.querySelectorAll('.skeleton-block').length,
      official: Object.fromEntries(['.ivu-input', '.ivu-select', '.ivu-date-picker', '.ivu-btn', '.ivu-table'].map(name => [name, document.querySelectorAll(name).length])),
      tableRowCount: document.querySelectorAll('.ivu-table-body tbody tr').length,
      missingText: names.filter(name => !content.includes(name)),
      missingFields: fields.filter(name => !inputs.some(value => value.includes(name))),
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      navCount: document.querySelectorAll('[data-nav-index]').length,
      filterCount: document.querySelectorAll('[data-filter-index]').length,
      actionCount: document.querySelectorAll('[data-action-index]').length,
    };
  }, { stage, tree });
}

async function main() {
  const input = resolve(arg('--input-dir') ?? '');
  const output = resolve(arg('--output-dir') ?? '');
  assert(arg('--input-dir') && arg('--output-dir'), 'Usage: --input-dir DIR --output-dir DIR');
  assert(output.startsWith(join(ROOT, 'artifacts') + '\\'), 'Use an artifacts output directory');
  try { assert((await readdir(output)).length === 0, 'Use a new empty output directory'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const tree = await read(join(input, 'source-tree.json'));
  const sourceImage = await readFile(join(input, 'prototype.png'));
  const review = await read(join(input, 'review.json'));
  const layoutIntent = await read(join(input, 'layout-intent.json'));
  assert(tree.sourceKind === 'prototype-screenshot', 'Input must be a prototype screenshot Tree');
  assert(tree.table.visibleRows > 0 && tree.table.columns.length === 9, 'Incomplete visible table structure');
  assert(review.sourceImageSha256 === hash(sourceImage) && review.contentTreeReview?.status === 'PASS',
    'Content Tree review must match the source screenshot');
  assert(layoutIntent.pattern === 'customer-list-page' && layoutIntent.decisions?.length >= 6,
    'Customer-list layout intent must be reviewed');
  const local = await readFile(join(ROOT, 'adapters/html/prototype-layout.css'), 'utf8');
  assertNoOfficialComponentOverrides(local, 'adapters/html/prototype-layout.css');
  const sourceLock = await verifySource();
  const current = await read(join(ROOT, 'registries/icons/current.json'));
  const registry = await read(join(ROOT, 'registries/icons/snapshots', current.snapshotSha256, 'registry.json'));
  const svg = {};
  for (const name of icons) {
    const id = `remix.${name}`;
    const descriptor = registry.icons[id];
    assert(descriptor?.status === 'source-ready', `missing_icon:${id}`);
    const bytes = await readFile(join(ROOT, 'registries/icons/objects', descriptor.svgSha256 + '.svg'));
    assert(hash(bytes) === descriptor.svgSha256, `icon_hash_mismatch:${id}`);
    svg[id] = bytes.toString('utf8');
  }
  const official = await officialCss();
  const bundled = await build({ entryPoints: [join(ROOT, 'adapters/html/prototype-layout.mjs')], bundle: true,
    write: false, platform: 'browser', format: 'esm', minify: true,
    define: { 'process.env.NODE_ENV': '"production"' } });
  const js = bundled.outputFiles[0].text;
  await mkdir(output, { recursive: true });
  const file = join(output, 'page.html');
  await writeFile(file, html({ tree, icons: svg }, official + '\n' + local, js), 'utf8');
  const report = { status: 'RUNNING', deliverable: false, sourceKind: tree.sourceKind,
    sourceImageSha256: hash(sourceImage), sourceTreeSha256: hash(await readFile(join(input, 'source-tree.json'))),
    sourceReviewSha256: hash(await readFile(join(input, 'review.json'))),
    layoutIntentSha256: hash(await readFile(join(input, 'layout-intent.json'))),
    officialSourceVersion: sourceLock.sourceVersion, page: 'page.html', pageSha256: hash(await readFile(file)),
    stages: {}, issues: [] };
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: tree.viewport, deviceScaleFactor: 1 });
    const runtimeErrors = [];
    page.on('pageerror', error => runtimeErrors.push(String(error)));
    await page.goto(pathToFileURL(file).href, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__designReady === true, { timeout: 30000 });
    for (const stage of ['skeleton', 'component', 'delivery']) {
      const findings = await inspect(page, stage, tree);
      const issues = [...runtimeErrors];
      if (findings.horizontalOverflow) issues.push('horizontal_overflow');
      if (stage === 'skeleton') {
        if (findings.skeletonBlockCount !== 1 + tree.navigation.length + 1 + 1 + 1 + tree.filters.length + tree.filterActions.length + tree.toolbarActions.length + 1)
          issues.push('skeleton_block_count_mismatch');
      } else {
        for (const [name, count] of Object.entries(findings.official)) if (!count) issues.push(`official_component_missing:${name}`);
        if (findings.navCount !== tree.navigation.length) issues.push('navigation_count_mismatch');
        if (findings.filterCount !== tree.filters.length) issues.push('filter_count_mismatch');
        if (findings.actionCount !== tree.toolbarActions.length) issues.push('toolbar_count_mismatch');
        if (findings.table && findings.tableWrap && Math.abs(findings.table.width - findings.tableWrap.width) > 2)
          issues.push('table_does_not_fill_card');
        if (stage === 'delivery') {
          if (findings.tableRowCount !== tree.table.visibleRows) issues.push('table_row_count_mismatch');
          issues.push(...findings.missingText.map(value => `missing_text:${value}`));
          issues.push(...findings.missingFields.map(value => `missing_field:${value}`));
        }
      }
      const image = await page.locator('.design-page').screenshot({ animations: 'disabled' });
      await writeFile(join(output, `${stage}.png`), image);
      report.stages[stage] = { status: issues.length ? 'FAIL' : 'PASS', screenshot: `${stage}.png`,
        screenshotSha256: hash(image), findings, issues };
      if (issues.length) { report.issues.push(...issues); break; }
    }
  } catch (error) { report.issues.push(String(error)); }
  finally { await browser.close(); }
  report.status = report.issues.length ? 'FAIL' : 'PASS';
  report.deliverable = report.status === 'PASS' && Object.keys(report.stages).length === 3;
  await writeFile(join(output, 'qa.json'), JSON.stringify(report, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({ status: report.status, deliverable: report.deliverable,
    stages: Object.fromEntries(Object.entries(report.stages).map(([stage, value]) => [stage, value.status])),
    issues: report.issues }));
  if (!report.deliverable) process.exitCode = 1;
}

await main();
