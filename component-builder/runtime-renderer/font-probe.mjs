import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, join, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { extractRuntime } from './extract.mjs';
import { ROOT, hash, jsonFile } from '../source-reader/source-lock.mjs';

// CDP reports fonts used by a node's child text nodes, not font-file identity.
// Keep shadow/pseudo observations distinct; empty usage is unknown, not a fallback.
export async function observeFonts(page, cases) {
  const session = await page.context().newCDPSession(page);
  try {
    await session.send('DOM.enable');
    await session.send('CSS.enable');
    const { root } = await session.send('DOM.getDocument', { depth: -1, pierce: true });
    const observations = [];
    async function walk(node, logicalId, path, surface = 'element') {
      if (node.nodeType === 1) {
        const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId: node.nodeId });
        observations.push({ logicalId, path, surface, tag: node.localName,
          status: fonts.some(font => font.glyphCount > 0) ? 'OBSERVED' : 'NO_GLYPHS_REPORTED', fonts });
      }
      let index = 0;
      for (const child of node.children ?? []) {
        if (child.nodeType === 1) await walk(child, logicalId, `${path}.${index++}`, surface);
      }
      for (const pseudo of node.pseudoElements ?? []) await walk(pseudo, logicalId, path, `pseudo:${pseudo.pseudoType}`);
      for (const shadow of node.shadowRoots ?? []) {
        let shadowIndex = 0;
        for (const child of shadow.children ?? []) {
          if (child.nodeType === 1) await walk(child, logicalId, `${path}.shadow.${shadowIndex++}`, 'user-agent-shadow');
        }
      }
    }
    for (const item of cases.cases) {
      const { nodeId } = await session.send('DOM.querySelector', {
        nodeId: root.nodeId, selector: `[data-runtime-case="${item.logicalId}"] > :first-child` });
      if (!nodeId) throw new Error('font_probe_missing_component: ' + item.logicalId);
      const { node } = await session.send('DOM.describeNode', { nodeId, depth: -1, pierce: true });
      // describeNode may omit frontend IDs for descendants; requestChildNodes populates them.
      await session.send('DOM.requestChildNodes', { nodeId, depth: -1, pierce: true });
      const find = current => current.nodeId === nodeId ? current :
        [...(current.children ?? []), ...(current.shadowRoots ?? [])].map(find).find(Boolean);
      await walk(find(root) ?? node, item.logicalId, '0');
    }
    return observations;
  } finally { await session.detach(); }
}

export async function probeFonts(outputDirectory, referenceDirectory) {
  const output = resolve(outputDirectory), reference = resolve(referenceDirectory);
  if (output === reference || output.startsWith(reference + '/') || output.startsWith(reference + '\\')) throw new Error('font_probe_reference_overwrite');
  for (const name of ['node_modules', 'component-builder', 'schemas', 'registries']) {
    const protectedPath = join(ROOT, name);
    if (output === protectedPath || output.startsWith(protectedPath + sep)) throw new Error('invalid_output_directory');
  }
  await mkdir(output, { recursive: true });
  await writeFile(join(output, 'font_report.json'), JSON.stringify({ scope: 'official_runtime_font_diagnostic', status: 'RUNNING', fidelityGate: 'NOT_RUN' }) + '\n');
  let evidence;
  try {
  const baseline = await jsonFile(join(reference, 'component_ir.json'));
  if (baseline.status !== 'PASS') throw new Error('font_probe_invalid_reference');
  const { result } = await extractRuntime(output, { observePage: async (page, context) => {
    evidence = { environment: context.environment, provenance: context.provenance,
      observations: await observeFonts(page, context.cases) };
  } });
  const matches = result.components.map(component => {
    const expected = baseline.components.find(item => item.logicalComponentId === component.logicalComponentId);
    return { logicalId: component.logicalComponentId, screenshotMatches: expected?.screenshot.sha256 === component.screenshot.sha256,
      environmentMatches: JSON.stringify(expected?.environment) === JSON.stringify(component.environment) };
  });
  const report = { scope: 'official_runtime_font_diagnostic', status: matches.every(item => item.screenshotMatches && item.environmentMatches) ? 'PASS' : 'REVIEW',
    referenceComponentIrSha256: hash(await readFile(join(reference, 'component_ir.json'))),
    referenceMatches: matches, ...evidence, fidelityGate: 'NOT_RUN',
    limitations: ['Node font usage is aggregated; no per-character mapping or system font-file hash.',
      'Empty font usage does not prove that a font is absent.', 'This diagnostic does not admit native components.'] };
  await writeFile(join(output, 'font_report.json'), JSON.stringify(report, null, 2) + '\n');
  return report;
  } catch (error) {
    await writeFile(join(output, 'font_report.json'), JSON.stringify({ scope: 'official_runtime_font_diagnostic', status: 'FAIL', fidelityGate: 'NOT_RUN', issues: [{ message: error.message }] }, null, 2) + '\n');
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const outputIndex = process.argv.indexOf('--output'), referenceIndex = process.argv.indexOf('--reference');
  if (outputIndex < 0 || referenceIndex < 0 || !process.argv[outputIndex + 1] || !process.argv[referenceIndex + 1]) throw new Error('Usage: font-probe.mjs --output <new directory> --reference <existing reference>');
  const report = await probeFonts(process.argv[outputIndex + 1], process.argv[referenceIndex + 1]);
  console.log(JSON.stringify({ status: report.status, referenceMatches: report.referenceMatches,
    observedFonts: [...new Set(report.observations.flatMap(item => item.fonts.map(font => font.familyName)))] }, null, 2));
}
