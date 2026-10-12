// Read installed versions, browser paths and the frozen source lock. No downloads or launches.
import {readFile, access} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {platform, arch} from 'node:os';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(root, 'package.json'));
const checks = [];
const add = (id, status, detail, extra = {}) => checks.push({id, status, detail, ...extra});
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const available = async path => {try {await access(path); return true;} catch {return false;}};
add('node', Number(process.versions.node.split('.')[0]) >= 24 ? 'PASS' : 'FAIL', process.version);
const pkg = await read(join(root, 'package.json'));
for (const [name, expected] of Object.entries(pkg.dependencies)) {
  try {
    const actual = (await read(join(root, 'node_modules', name, 'package.json'))).version;
    add('node-package:' + name, actual === expected ? 'PASS' : 'FAIL', actual, {expectedVersion: expected});
  } catch (error) {add('node-package:' + name, error.code === 'ENOENT' ? 'MISSING' : 'FAIL', String(error));}
}
try {
  const {chromium} = await import('playwright');
  const full = chromium.executablePath();
  add('chromium', await available(full) ? 'PASS' : 'MISSING', full);
  // Tests use both the explicit full Chromium and Playwright's default headless shell.
  const metadata = await read(join(dirname(require.resolve('playwright-core/package.json')), 'browsers.json'));
  const browser = metadata.browsers.find(b => b.name === 'chromium-headless-shell');
  const folders = {win32: ['chrome-headless-shell-win64', 'chrome-headless-shell.exe'],
    linux: ['chrome-headless-shell-linux64', 'chrome-headless-shell'],
    darwin: [`chrome-headless-shell-mac-${arch() === 'arm64' ? 'arm64' : 'x64'}`, 'chrome-headless-shell']};
  const folder = folders[platform()];
  if (!folder || !browser) throw new Error('Unsupported headless-shell platform or metadata');
  const shell = join(dirname(dirname(dirname(full))), `chromium_headless_shell-${browser.revision}`, ...folder);
  add('chromium-headless-shell', await available(shell) ? 'PASS' : 'MISSING', shell);
} catch (error) {add('browser-probe', error.code === 'ERR_MODULE_NOT_FOUND' ? 'MISSING' : 'FAIL', String(error));}
try {
  const {verifySource} = await import('../component-builder/source-reader/source-lock.mjs');
  await verifySource();
  add('official-source-lock', 'PASS', 'Installed package/source/CSS bytes match the frozen lock');
} catch (error) {add('official-source-lock', error.code === 'ENOENT' ? 'MISSING' : 'FAIL', String(error));}
console.log(JSON.stringify({checks}));
