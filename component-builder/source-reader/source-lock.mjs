import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const LOCK_PATH = join(ROOT, 'component-builder/source-reader/source-lock.json');
export const hash = data => createHash('sha256').update(data).digest('hex');
export const jsonFile = async path => JSON.parse(await readFile(path, 'utf8'));

export async function packageFiles(directory) {
  const result = [];
  for (const entry of (await readdir(directory, { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    const path = join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error('source_symlink_forbidden: ' + path);
    if (entry.isDirectory()) result.push(...await packageFiles(path));
    else if (entry.isFile()) result.push(path);
  }
  return result;
}

export async function sourceSnapshot() {
  const files = ['package.json', 'package-lock.json'];
  for (const name of ['view-ui-plus', 'vue', '@vue/shared', '@vue/reactivity', '@vue/runtime-core', '@vue/runtime-dom', '@vue/compiler-core', '@vue/compiler-dom']) {
    files.push(...(await packageFiles(join(ROOT, 'node_modules', name))).map(path => relative(ROOT, path).replaceAll('\\', '/')));
  }
  const result = {};
  for (const name of files.sort()) result[name] = hash(await readFile(join(ROOT, name)));
  return result;
}

export async function verifySource(lock = undefined) {
  lock ??= await jsonFile(LOCK_PATH);
  const current = await sourceSnapshot();
  if (lock.lockVersion !== '0.1.0' || hash(JSON.stringify(lock.files)) !== lock.filesSha256 || lock.sourceVersion !== `${lock.packageName}@${lock.packageVersion}+${lock.gitCommit}` || !/^[0-9a-f]{40}$/.test(lock.gitCommit)) throw new Error('invalid_source_lock');
  if (JSON.stringify(current) !== JSON.stringify(lock.files)) throw new Error('source_lock_mismatch: package/source/CSS changed; no automatic version switch');
  const pkg = await jsonFile(join(ROOT, 'node_modules/view-ui-plus/package.json'));
  if (pkg.name !== lock.packageName || pkg.version !== lock.packageVersion) throw new Error('source_version_mismatch');
  return lock;
}
