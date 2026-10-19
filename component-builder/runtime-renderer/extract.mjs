import { chromium } from 'playwright';
import { build } from 'esbuild';
import { createServer } from 'node:http';
import { listenBrowserLoopback } from './loopback-server.mjs';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { join, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { platform, release } from 'node:os';
import { ROOT, verifySource, hash, jsonFile, LOCK_PATH } from '../source-reader/source-lock.mjs';
import { captureComponent } from '../style-extractor/capture.mjs';
import { assembleComponentIr } from '../component-ir/assemble.mjs';

export async function extractRuntime(outputDirectory, { observePage, casesData, casesPath = join(ROOT,'component-builder/runtime-renderer/cases.json'), harnessPath = join(ROOT,'component-builder/runtime-renderer/harness.js') } = {}) {
  if (observePage !== undefined && typeof observePage !== 'function') throw new Error('invalid_runtime_observer');
  const output = resolve(outputDirectory);
  for (const protectedDirectory of [join(ROOT, 'node_modules'), join(ROOT, 'component-builder'), join(ROOT, 'schemas'), join(ROOT, 'registries')]) {
    if (output === protectedDirectory || output.startsWith(protectedDirectory + sep)) throw new Error('invalid_output_directory: cannot overwrite sources');
  }
  await mkdir(output, { recursive: true });
  const reportPath = join(output, 'extraction_report.json');
  const bundlePath = join(output, 'component_ir.json');
  const writeJson = (path, value) => writeFile(path, JSON.stringify(value, null, 2) + '\n', 'utf8');
  // Invalidate any prior success before starting, so exceptions cannot reuse old IR.
  await writeJson(reportPath, { scope: 'component_runtime_extraction', status: 'RUNNING' });
  await writeJson(bundlePath, { status: 'RUNNING', components: [] });
  let browser, server;
  try {
    const lock = await verifySource();
    for (const input of [casesPath,harnessPath]) if (!resolve(input).startsWith(resolve(ROOT,'component-builder/runtime-renderer')+sep)) throw new Error('invalid_runtime_fixture_path');
    // Generated fixtures are passed as data, never written over frozen source cases.
    const casesBytes = casesData === undefined ? await readFile(casesPath) : Buffer.from(JSON.stringify(casesData));
    const cases = JSON.parse(casesBytes.toString('utf8'));
    const identities = new Set();
    if (cases.casesVersion !== '0.1.0' || !Number.isFinite(cases.containerWidth) || cases.containerWidth <= 0 || !Array.isArray(cases.cases)) throw new Error('invalid_runtime_cases');
    for (const item of cases.cases) {
      if (!/^[a-zA-Z][a-zA-Z0-9_.-]*$/.test(item.logicalId) || identities.has(item.logicalId) || !['Button', 'Input', 'Select', 'Table', 'Tag', 'Checkbox', 'Radio', 'Switch', 'Card', 'Pagination', 'Tabs', 'Tree', 'DatePicker'].includes(item.componentType) || !item.props || typeof item.props !== 'object') throw new Error('invalid_runtime_case');
      if (Object.keys(item.props).some(name => ['style', 'class', 'innerHTML', 'textContent'].includes(name) || name.startsWith('on'))) throw new Error('component_css_override_forbidden');
      identities.add(item.logicalId);
    }
    const bundled = await build({ entryPoints: [harnessPath], bundle: true, write: false, format: 'esm', platform: 'browser', metafile: true, define: { 'process.env.NODE_ENV': '"production"' }, plugins: casesData === undefined ? [] : [{name:'runtime-cases',setup(builder){
      builder.onResolve({filter:/^ui-design-skill:runtime-cases$/},()=>({path:'cases',namespace:'runtime-cases'}));
      builder.onLoad({filter:/.*/,namespace:'runtime-cases'},()=>({contents:casesBytes.toString('utf8'),loader:'json'}));
    }}] });
    const js = bundled.outputFiles[0].contents;
    const html = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><link rel="stylesheet" href="/vendor/styles/viewuiplus.css"></head><body><div id="app"></div><script type="module" src="/harness.js"></script></body></html>';
    const requests = [], errors = [];
    server = createServer(async (request, response) => {
      try {
        const route = new URL(request.url, 'http://localhost').pathname;
        let body, mime;
        if (route === '/') { body = html; mime = 'text/html; charset=utf-8'; }
        else if (route === '/harness.js') { body = js; mime = 'text/javascript; charset=utf-8'; }
        else if (route.startsWith('/vendor/')) {
          const vendor = resolve(ROOT, 'node_modules/view-ui-plus/dist');
          const path = resolve(vendor, '.' + route.slice('/vendor'.length));
          if (!path.startsWith(vendor + sep)) throw new Error('Invalid vendor path');
          body = await readFile(path);
          mime = path.endsWith('.css') ? 'text/css' : path.endsWith('.woff2') ? 'font/woff2' : path.endsWith('.woff') ? 'font/woff' : 'application/octet-stream';
        } else { response.writeHead(404); response.end(); return; }
        requests.push({ path: route, sha256: hash(body), bytes: Buffer.byteLength(body) });
        response.writeHead(200, { 'Content-Type': mime }); response.end(body);
      } catch (error) { errors.push(String(error)); response.writeHead(500); response.end(); }
    });
    await listenBrowserLoopback(server);
    const browserPath = chromium.executablePath();
    browser = await chromium.launch({ headless: true, executablePath: browserPath });
    const context = await browser.newContext({ viewport: cases.viewport, deviceScaleFactor: 1, locale: 'zh-CN', colorScheme: 'light', reducedMotion: 'reduce' });
    await context.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort());
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    page.on('requestfailed', request => errors.push(`request_failed: ${new URL(request.url()).pathname}`));
    page.on('response', response => { if (response.status() >= 400) errors.push(`http_${response.status()}: ${new URL(response.url()).pathname}`); });
    await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__runtimeMounted === true);
    await page.evaluate(async () => { await document.fonts.ready; await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
    const environment = { browser: browser.version(), browserExecutableSha256: hash(await readFile(browserPath)), node: process.version,
      operatingSystem: { platform: platform(), release: release() }, viewport: cases.viewport, deviceScaleFactor: 1, locale: 'zh-CN', fontsStatus: await page.evaluate(() => document.fonts.status) };
    const provenance = { sourceVersion: lock.sourceVersion, sourceLockSha256: hash(await readFile(LOCK_PATH)), packageVersion: lock.packageVersion,
      officialCssSha256: lock.files['node_modules/view-ui-plus/dist/styles/viewuiplus.css'], officialRuntimeSha256: lock.files['node_modules/view-ui-plus/dist/viewuiplus.min.js'],
      casesSha256: hash(casesBytes), harnessBundleSha256: hash(js),
      extractorSha256: hash(await readFile(join(ROOT, 'component-builder/style-extractor/capture.mjs'))),
      assemblySha256: hash(await readFile(join(ROOT, 'component-builder/component-ir/assemble.mjs'))),
      rendererSha256: hash(await readFile(join(ROOT, 'component-builder/runtime-renderer/extract.mjs'))) };
    if (observePage) await observePage(page, { cases, environment, provenance });
    const components = [];
    const resolvedProps = await page.evaluate(() => window.__runtimeResolvedProps());
    for (const item of cases.cases) {
      const captured = await page.evaluate(captureComponent, item.logicalId);
      if (Object.keys(item.props).some(name => !Object.hasOwn(resolvedProps[item.logicalId], name))) throw new Error('unknown_official_prop: ' + item.logicalId);
      if (captured.rootBounds.width <= 0 || captured.rootBounds.height <= 0) throw new Error('empty_runtime_component: ' + item.logicalId);
      const screenshotName = item.logicalId + '.png';
      const screenshot = await page.locator(`[data-runtime-case="${item.logicalId}"] > :first-child`).screenshot({ animations: 'disabled' });
      await writeFile(join(output, screenshotName), screenshot);
      components.push(assembleComponentIr(item, captured, resolvedProps[item.logicalId], { containerWidth: cases.containerWidth, provenance, environment }, { path: screenshotName, sha256: hash(screenshot) }));
    }
    if (errors.length) throw new Error('runtime_errors: ' + errors.join('; '));
    await verifySource(lock);
    const gallery = await page.screenshot({ animations: 'disabled' });
    await writeFile(join(output, 'official-runtime-gallery.png'), gallery);
    const manifest = { scope: 'official_runtime_evidence', source: lock, provenance, environment,
      runtimeSupportFiles: {'component-builder/runtime-renderer/loopback-server.mjs':hash(await readFile(join(ROOT,'component-builder/runtime-renderer/loopback-server.mjs')))},
      servedResources: requests.sort((a, b) => a.path.localeCompare(b.path, 'en')), gallerySha256: hash(gallery) };
    await writeJson(join(output, 'runtime_manifest.json'), manifest);
    const result = { status: 'PASS', componentIrVersion: '0.1.0', components };
    await writeJson(bundlePath, result);
    const report = { scope: 'component_runtime_extraction', status: 'PASS', sourceVersion: lock.sourceVersion,
      componentTypes: components.map(item => item.componentType), componentIrSha256: hash(await readFile(bundlePath)),
      runtimeManifestSha256: hash(await readFile(join(output, 'runtime_manifest.json'))), fidelityGate: 'NOT_RUN', issues: [] };
    await writeJson(reportPath, report);
    return { report, result };
  } catch (error) {
    await writeJson(bundlePath, { status: 'FAIL', components: [] });
    await writeJson(reportPath, { scope: 'component_runtime_extraction', status: 'FAIL', fidelityGate: 'NOT_RUN', issues: [{ code: String(error.message).split(':')[0], message: String(error.message) }] });
    throw error;
  } finally {
    await browser?.close();
    if (server) await new Promise(resolve => server.close(resolve));
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const index = process.argv.indexOf('--output');
  if (index < 0 || !process.argv[index + 1]) throw new Error('Usage: extract.mjs --output <directory>');
  const { report } = await extractRuntime(process.argv[index + 1]);
  console.log(JSON.stringify(report, null, 2));
}
