import { writeFile, access } from 'node:fs/promises';
import { join } from 'node:path';
import { ROOT, LOCK_PATH, jsonFile, sourceSnapshot, hash } from './source-lock.mjs';

try {
  await access(LOCK_PATH);
  throw new Error('source_lock_exists: keep this task version locked; an explicit new source snapshot is required for migration');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const pkg = await jsonFile(join(ROOT, 'node_modules/view-ui-plus/package.json'));
const npmLock = await jsonFile(join(ROOT, 'package-lock.json'));
const response = await fetch(`https://registry.npmjs.org/view-ui-plus/${pkg.version}`);
if (!response.ok) throw new Error('official_metadata_unavailable');
const published = await response.json();
const installed = npmLock.packages['node_modules/view-ui-plus'];
const repository = published.repository.url.replace(/^git\+/, '').replace(/\.git$/, '');
if (published.name !== 'view-ui-plus' || repository !== 'https://github.com/view-design/ViewUIPlus' || installed.integrity !== published.dist.integrity || installed.resolved !== published.dist.tarball) throw new Error('official_source_mismatch');
const files = await sourceSnapshot();
const lock = { lockVersion: '0.1.0', packageName: pkg.name, packageVersion: pkg.version,
  sourceVersion: `${pkg.name}@${pkg.version}+${published.gitHead}`, repository,
  gitCommit: published.gitHead, registryUrl: response.url, tarball: published.dist.tarball,
  npmIntegrity: published.dist.integrity, filesSha256: hash(JSON.stringify(files)), files };
await writeFile(LOCK_PATH, JSON.stringify(lock, null, 2) + '\n', 'utf8');
console.log(JSON.stringify({ sourceVersion: lock.sourceVersion, files: Object.keys(files).length, filesSha256: lock.filesSha256 }));
