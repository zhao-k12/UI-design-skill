// Replay the frozen official fixture twice; retain independent raw runs and exact-byte comparisons.
import {readFile, writeFile, mkdir, realpath} from 'node:fs/promises';
import {join, resolve, sep} from 'node:path';
import {pathToFileURL} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {extractRuntime} from '../component-builder/runtime-renderer/extract.mjs';
import {ROOT, hash, jsonFile, verifySource, LOCK_PATH} from '../component-builder/source-reader/source-lock.mjs';

const write = (path, value) => writeFile(path, JSON.stringify(value, null, 2) + '\n', 'utf8');

export async function compareRuns(first, second) {
  const issues = [];
  const records = [];
  const left = await jsonFile(join(first, 'component_ir.json'));
  const right = await jsonFile(join(second, 'component_ir.json'));
  const reports = await Promise.all([first, second].map(base => jsonFile(join(base, 'extraction_report.json'))));
  if (left.status !== 'PASS' || right.status !== 'PASS' || reports.some(r => r.status !== 'PASS'))
    issues.push({code: 'extraction_not_pass'});
  if (!isDeepStrictEqual(left, right)) issues.push({code: 'component_ir_not_repeatable'});
  if (!isDeepStrictEqual(reports[0], reports[1])) issues.push({code: 'extraction_report_not_repeatable'});
  // No tolerance, normalization, screenshot conversion or masking.
  const names = ['component_ir.json', 'extraction_report.json', 'runtime_manifest.json', 'official-runtime-gallery.png'];
  for (const component of left.components ?? []) {
    const path = component.screenshot?.path;
    if (typeof path !== 'string' || path.includes('/') || path.includes('\\') || path === '.' || path === '..')
      throw new Error('invalid_replay_screenshot_path');
    names.push(path);
  }
  for (const name of [...new Set(names)].sort()) {
    const bytes = await Promise.all([first, second].map(base => readFile(join(base, name))));
    const hashes = bytes.map(hash);
    const equal = hashes[0] === hashes[1];
    records.push({path: name, firstSha256: hashes[0], secondSha256: hashes[1], equal});
    if (!equal) issues.push({code: 'runtime_bytes_not_repeatable', path: name});
  }
  return {status: issues.length ? 'FAIL' : 'PASS', issues, files: records,
    componentTypes: (left.components ?? []).map(c => c.componentType),
    sourceVersion: reports[0].sourceVersion};
}

export async function replay(outputDir) {
  const output = resolve(outputDir), artifacts = resolve(ROOT, 'artifacts');
  if (!output.startsWith(artifacts + sep)) throw new Error('Use a new artifacts child directory');
  // mkdir without recursive creation at the final path rejects even an empty existing directory.
  let existing = resolve(output, '..');
  while (true) {
    try {await realpath(existing); break;}
    catch (error) {if (error.code !== 'ENOENT') throw error; existing = resolve(existing, '..');}
  }
  const ancestor = await realpath(existing);
  if (!ancestor.startsWith(artifacts + sep) && ancestor !== artifacts)
    throw new Error('Output ancestor escapes artifacts');
  await mkdir(resolve(output, '..'), {recursive: true});
  const parent = await realpath(resolve(output, '..'));
  if (!parent.startsWith(artifacts + sep) && parent !== artifacts)
    throw new Error('Output parent escapes artifacts');
  await mkdir(output);
  const packet = {scope: 'official-runtime-replay', version: '0.1.0', status: 'RUNNING',
    sourceLockSha256: hash(await readFile(LOCK_PATH)),
    nativeExecution: 'NOT_RUN', nativeAcceptance: 'NOT_RUN', releaseReady: false,
    runs: [], issues: []};
  const reportPath = join(output, 'replay_report.json');
  await write(reportPath, packet);
  try {
    const source = await verifySource();
    packet.sourceVersion = source.sourceVersion;
    const metadata = await jsonFile(join(ROOT, 'node_modules/playwright-core/browsers.json'));
    packet.expectedBrowserVersion = metadata.browsers.find(b => b.name === 'chromium').browserVersion;
    for (const name of ['first', 'second']) {
      const directory = join(output, name);
      await extractRuntime(directory);
      const bundle = await jsonFile(join(directory, 'component_ir.json'));
      if (bundle.components.some(c => c.environment.browser !== packet.expectedBrowserVersion))
        throw new Error('Browser version differs from the installed Playwright metadata');
      packet.runs.push({directory: name, status: 'PASS',
        extractionReportSha256: hash(await readFile(join(directory, 'extraction_report.json')))});
      await write(reportPath, packet);
    }
    packet.comparison = await compareRuns(join(output, 'first'), join(output, 'second'));
    packet.status = packet.comparison.status;
    packet.issues = packet.comparison.issues;
    await verifySource();
  } catch (error) {
    packet.status = 'FAIL';
    packet.issues.push({code: 'runtime_replay_failed', detail: String(error)});
  }
  await write(reportPath, packet);
  return packet;
}

async function main() {
  if (process.argv.length !== 4 || process.argv[2] !== '--output-dir') {
    console.error('Usage: node scripts/runtime_replay.mjs --output-dir artifacts/new-task/replay');
    return 2;
  }
  try {
    const packet = await replay(process.argv[3]);
    console.log(JSON.stringify(packet));
    return packet.status === 'PASS' ? 0 : 1;
  } catch (error) {
    console.error(String(error));
    return 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href)
  process.exitCode = await main();
