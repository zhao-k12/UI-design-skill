// QA preview of byte-exact official SVGs. This does not create platform components.
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const store = path.join(root, 'registries/icons');
const pointer = JSON.parse(await readFile(path.join(store, 'current.json'), 'utf8'));
if (!/^[a-f0-9]{64}$/.test(pointer.snapshotSha256)) throw new Error('Invalid snapshot');
const data = JSON.parse(await readFile(path.join(store, 'snapshots', pointer.snapshotSha256, 'registry.json'), 'utf8'));
const samples = [
  ['搜索', 'remix.search-line'], ['删除', 'remix.delete-bin-line'], ['新增', 'remix.add-line'],
  ['导出', 'remix.download-line'], ['设置', 'remix.settings-3-line']
];
const cards = [];
for (const [label, id] of samples) {
  const descriptor = data.icons[id];
  if (!descriptor || descriptor.status !== 'source-ready' || !/^[a-f0-9]{64}$/.test(descriptor.svgSha256)) throw new Error('Missing official SVG');
  const raw = await readFile(path.join(store, 'objects', `${descriptor.svgSha256}.svg`));
  if (createHash('sha256').update(raw).digest('hex') !== descriptor.svgSha256) throw new Error('Official SVG changed');
  const svg = raw.toString('utf8');
  cards.push(`<section>${svg}<strong>${label}</strong><span>${id}</span></section>`);
}
const output = path.join(root, 'artifacts/task-008');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: chromium.executablePath(), headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1000, height: 210 }, deviceScaleFactor: 1 });
  await page.route('**/*', route => route.abort());
  await page.setContent(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>
    body{margin:0;padding:24px;background:#fff;color:#17233d;font-family:Arial,'Microsoft YaHei',sans-serif}
    h1{font-size:18px;margin:0 0 24px} main{display:flex;gap:16px}section{display:flex;width:178px;align-items:center;flex-direction:column;gap:12px}
    svg{width:24px;height:24px}strong{font-size:14px}span{font-size:10px}
    </style><h1>Remix Icon ${data.sourceVersion.split('@')[1].split('+')[0]} · 官方 SVG 来源预览</h1><main>${cards.join('')}</main></html>`);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(output, 'official-icon-gallery.png') });
  await writeFile(path.join(output, 'icon_preview_report.json'), JSON.stringify({
    scope: 'official_svg_browser_preview', status: 'PASS', browser: browser.version(),
    sourceVersion: data.sourceVersion, samples: samples.map(([query, iconId]) => ({query, iconId})), nativePlatformApplication: 'NOT_RUN'
  }, null, 2) + '\n');
} finally {
  await browser.close();
}
