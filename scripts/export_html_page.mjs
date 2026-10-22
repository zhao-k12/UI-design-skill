// Export the verified prototype workflow to three self-contained HTML pages.
import { build } from 'esbuild';
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import { resolve, join, dirname, extname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT, verifySource } from '../component-builder/source-reader/source-lock.mjs';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const arg = name => { const at = process.argv.indexOf(name); return at < 0 ? undefined : process.argv[at + 1]; };
const walk = (node, fn) => { fn(node); for (const child of node.children ?? []) walk(child, fn); };
const claimTexts = value => {
  if (!value || typeof value !== 'object') return [];
  if (typeof value.text === 'string' && Array.isArray(value.evidence)) return [value.text];
  return Object.values(value).flatMap(claimTexts);
};

async function officialCss() {
  const source = join(ROOT, 'node_modules/view-ui-plus/dist/styles/viewuiplus.css');
  let css = await readFile(source, 'utf8');
  const references = [...css.matchAll(/url\((['"]?)([^)'"\s]+)\1\)/g)];
  for (const [, , raw] of references) {
    if (/^(data:|https?:|#)/i.test(raw)) continue;
    const file = resolve(dirname(source), raw.split(/[?#]/)[0]);
    assert(file.startsWith(join(ROOT, 'node_modules/view-ui-plus/dist')), 'CSS asset outside locked official package');
    const bytes = await readFile(file);
    const mime = { '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.svg': 'image/svg+xml', '.png': 'image/png' }[extname(file)] ?? 'application/octet-stream';
    css = css.replaceAll(raw, `data:${mime};base64,${bytes.toString('base64')}`);
  }
  return css;
}

function html(payload, js, css) {
  const json = JSON.stringify(payload).replaceAll('<', '\\u003c');
  const title = payload.stage === 'skeleton' ? '彩色组件骨架' : payload.stage === 'default' ? '默认文案组件页' : '原型内容页面';
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>${css}</style><style>html,body{margin:0;min-width:320px;background:#f5f7f9}#app{width:max-content;min-width:100%}.component-cell{display:block}.component-cell>.ivu-table-wrapper{width:100%}.page-icon svg{width:100%;height:100%}.skeleton-cell{box-sizing:border-box;border:1px solid #64748b;border-radius:3px;overflow:hidden;padding:4px;color:#334155;font:12px/16px Inter,Arial,sans-serif;white-space:nowrap}</style></head><body><div id="app"></div><script type="application/json" id="design-payload">${json}</script><script type="module">${js.replaceAll('</script', '<\\/script')}</script></body></html>`;
}

async function inspect(browser, file, payload) {
  const page = await browser.newPage({ viewport: { width: Math.max(1280, payload.document.pages[0].layout.width.value), height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(pathToFileURL(file).href, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__designReady === true, { timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  const findings = await page.evaluate(({ stage, expectedCells }) => {
    const all = [...document.querySelectorAll('[data-source-id]')];
    const cells = [...document.querySelectorAll('[data-cell-id]')];
    const components = [...document.querySelectorAll('[data-component-type]')];
    const table = document.querySelector('.ivu-table');
    const tableHost = document.querySelector('[data-component-type="Table"]');
    return { stage, cellCount: cells.length, componentCount: components.length,
      sourceIds: [...new Set(all.map(node => node.dataset.sourceId).filter(Boolean))],
      componentTypes: components.map(node => node.dataset.componentType),
      tableWidth: table?.getBoundingClientRect().width ?? null,
      tableCellWidth: tableHost?.getBoundingClientRect().width ?? null,
      pageWidth: document.querySelector('.design-page,.skeleton-page')?.getBoundingClientRect().width ?? null,
      horizontalOverflow: document.documentElement.scrollWidth > document.querySelector('.design-page,.skeleton-page')?.getBoundingClientRect().width + 1,
      overflowNodes: [...document.querySelectorAll('[data-node-id]')].filter(node => node.getBoundingClientRect().right > (document.querySelector('.design-page,.skeleton-page')?.getBoundingClientRect().right ?? Infinity) + 1).slice(0, 12).map(node => [node.dataset.nodeId, Math.round(node.getBoundingClientRect().left), Math.round(node.getBoundingClientRect().right)]),
      componentBoxes: components.map(node => [node.dataset.nodeId, ...[node.getBoundingClientRect().x, node.getBoundingClientRect().y, node.getBoundingClientRect().width].map(Math.round)]),
      cellGeometry: Object.fromEntries(expectedCells.map(cell => {
        const node = document.querySelector(`[data-node-id="${cell.cellId}"],[data-cell-id="${cell.cellId}"]`);
        const box = node?.getBoundingClientRect();
        return [cell.cellId, box ? { x: box.x, y: box.y, width: box.width, height: box.height } : null];
      })),
      nativeClasses: components.map(node => [node.dataset.componentType,
        ({ Input: '.ivu-input', Select: '.ivu-select', Button: '.ivu-btn', Table: '.ivu-table' }[node.dataset.componentType]
          ? Boolean(node.querySelector(({ Input: '.ivu-input', Select: '.ivu-select', Button: '.ivu-btn', Table: '.ivu-table' })[node.dataset.componentType])) : true)]),
      text: document.body.innerText,
      htmlBySource: Object.fromEntries([...new Set(all.map(node => node.dataset.sourceId).filter(Boolean))].map(id => [id, all.filter(node => node.dataset.sourceId === id).map(node => {
        const inputs = [...node.querySelectorAll('input')].map(input => `${input.value} ${input.placeholder}`).join(' ');
        return `${node.innerText ?? ''} ${inputs}`;
      }).join(' ')])) };
  }, { stage: payload.stage, expectedCells: payload.skeleton.cells });
  const png = await page.locator('.design-page,.skeleton-page').screenshot({ animations: 'disabled' });
  await page.close();
  return { findings, png, errors };
}

async function main() {
  const core = resolve(arg('--core-dir') ?? '');
  const staged = resolve(arg('--staged-dir') ?? '');
  const source = resolve(arg('--source-dir') ?? '');
  const output = resolve(arg('--output-dir') ?? '');
  assert(arg('--core-dir') && arg('--staged-dir') && arg('--source-dir') && arg('--output-dir'), 'Usage: --core-dir DIR --staged-dir DIR --source-dir DIR --output-dir DIR');
  assert(output.startsWith(join(ROOT, 'artifacts') + '\\'), 'Use an artifacts task output directory');
  try { assert((await readdir(output)).length === 0, 'Use a new empty HTML output directory'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const python = process.env.PYTHON ?? join(ROOT, '.venv/Scripts/python.exe');
  const validation = spawnSync(python, [join(ROOT, 'scripts/validate_html_inputs.py'), '--core-dir', core,
    '--staged-dir', staged, '--source-dir', source], { cwd: ROOT, encoding: 'utf8' });
  assert(validation.status === 0, `HTML input binding failed: ${validation.stderr || validation.stdout}`);
  const sourceLock = await verifySource();
  const coreQa = await read(join(core, 'qa_report.json'));
  assert(coreQa.status === 'PASS' && coreQa.readyForAdapter === true, 'Core QA must PASS');
  for (const file of ['layout_quality_qa.json', 'iview_conformance_qa.json']) {
    assert((await read(join(staged, file))).status === 'PASS', `${file} must PASS`);
  }
  const document = await read(join(core, 'final_ui_ir.json'));
  const defaultDocument = await read(join(staged, 'default_component_page_ui_ir.json'));
  const skeleton = await read(join(staged, 'annotated_skeleton_page.json'));
  const tree = await read(join(staged, 'page_content_tree.json'));
  const version = (await read(join(core, 'manifest.json'))).versions?.component_library_version ??
    (await read(join(core, 'manifest.json'))).versions?.componentLibraryVersion;
  const fallback = arg('--catalog') ?? 'registries/components/v0.2.9/catalog.json';
  const catalogPath = version && /^0\.2\.\d+/.test(version) ? join(ROOT, 'registries/components', `v${version.match(/^0\.2\.\d+/)[0]}`, 'catalog.json') : join(ROOT, fallback);
  const catalog = await read(catalogPath);
  const tokens = (await read(join(ROOT, 'registries/tokens/v0.2.3/default.json'))).tokens;
  const sourceIds = new Set(tree.sections.flatMap(section => section.items.map(item => item.id)));
  const content = Object.fromEntries(tree.sections.flatMap(section => section.items.map(item => [item.id, item.sourceContent])));
  assert(sourceIds.size === Object.keys(content).length, 'Content Tree source IDs must be unique');
  const components = [];
  const iconIds = new Set();
  for (const page of document.pages) walk(page, node => {
    if (node.type === 'ComponentInstance') components.push(node);
    if (node.type === 'IconInstance') iconIds.add(node.iconId);
  });
  for (const node of components) assert(catalog.components[node.componentId]?.status === 'active', `unregistered_component:${node.componentId}`);
  const current = await read(join(ROOT, 'registries/icons/current.json'));
  const registry = await read(join(ROOT, 'registries/icons/snapshots', current.snapshotSha256, 'registry.json'));
  const icons = {};
  for (const id of iconIds) {
    const descriptor = registry.icons[id];
    assert(descriptor?.status === 'source-ready', `missing_icon:${id}`);
    const svg = await readFile(join(ROOT, 'registries/icons/objects', descriptor.svgSha256 + '.svg'), 'utf8');
    assert(hash(svg) === descriptor.svgSha256, `icon_hash_mismatch:${id}`);
    icons[id] = svg;
  }
  const bundled = await build({ entryPoints: [join(ROOT, 'adapters/html/browser.mjs')], bundle: true, write: false, platform: 'browser', format: 'esm', minify: true, define: { 'process.env.NODE_ENV': '"production"' } });
  const js = bundled.outputFiles[0].text;
  const css = await officialCss();
  await mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const report = { status: 'RUNNING', scope: 'html-prototype-workflow', sourceVersion: sourceLock.sourceVersion,
    officialCssSha256: sourceLock.files['node_modules/view-ui-plus/dist/styles/viewuiplus.css'],
    catalogSha256: hash(await readFile(catalogPath)), coreUiIrSha256: hash(await readFile(join(core, 'final_ui_ir.json'))),
    contentTreeSha256: hash(await readFile(join(staged, 'page_content_tree.json'))), stages: {}, issues: [] };
  try {
    for (const stage of ['skeleton', 'default', 'final']) {
      const payload = { stage, document: stage === 'default' ? defaultDocument : document,
        skeleton, catalog: catalog.components, content, icons, tokens, minPageHeight: Number(tokens['size.page-min-height'].value) };
      const file = join(output, `${stage}.html`);
      await writeFile(file, html(payload, js, css), 'utf8');
      let findings, png, errors;
      try { ({ findings, png, errors } = await inspect(browser, file, payload)); }
      catch (error) {
        const issue = `browser_render_failed:${stage}:${String(error.message)}`;
        report.stages[stage] = { status: 'FAIL', html: `${stage}.html`, htmlSha256: hash(await readFile(file)), issues: [issue] };
        report.issues.push(issue);
        break;
      }
      const issues = [...errors];
      if (stage === 'skeleton') {
        if (findings.cellCount !== skeleton.cells.length) issues.push('skeleton_cell_count_mismatch');
        for (const id of sourceIds) if (!findings.sourceIds.includes(id)) issues.push(`skeleton_missing_source:${id}`);
      } else {
        if (findings.componentCount !== components.length) issues.push('component_count_mismatch');
        for (const id of sourceIds) if (!findings.sourceIds.includes(id)) issues.push(`${stage}_missing_source:${id}`);
        if (findings.tableWidth !== null && Math.abs(findings.tableWidth - findings.tableCellWidth) > 2) issues.push('table_does_not_fill_cell');
        for (const [kind, found] of findings.nativeClasses) if (!found) issues.push(`official_component_dom_missing:${kind}`);
        if (stage === 'final') for (const [id, value] of Object.entries(content))
          for (const claim of claimTexts(value)) if (!findings.htmlBySource[id]?.includes(claim)) issues.push(`missing_prototype_text:${id}:${claim}`);
      }
      for (const cell of skeleton.cells) {
        const actual = findings.cellGeometry[cell.cellId];
        if (!actual || ['x', 'y', 'width', 'height'].some(axis => Math.abs(actual[axis] - cell.box[axis]) > 1))
          issues.push(`cell_geometry_mismatch:${cell.cellId}`);
      }
      if (findings.horizontalOverflow) issues.push('horizontal_overflow');
      await writeFile(join(output, `${stage}.png`), png);
      report.stages[stage] = { status: issues.length ? 'FAIL' : 'PASS', html: `${stage}.html`, htmlSha256: hash(await readFile(file)),
        png: `${stage}.png`, pngSha256: hash(png), findings: { ...findings, text: undefined, htmlBySource: undefined }, issues };
      if (issues.length) { report.issues.push(...issues); break; }
    }
  } finally { await browser.close(); }
  report.status = report.issues.length ? 'FAIL' : 'PASS';
  report.deliverable = report.status === 'PASS' && Object.keys(report.stages).length === 3;
  await writeFile(join(output, 'html_workflow_qa.json'), JSON.stringify(report, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({ status: report.status, deliverable: report.deliverable, stages: Object.fromEntries(Object.entries(report.stages).map(([key, value]) => [key, value.status])), issues: report.issues }));
  if (!report.deliverable) process.exitCode = 1;
}

await main();
