"""Windows fallback: install pinned browser archives fetched from Google's official bucket."""
import argparse
import base64
from hashlib import md5, sha256
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def extract_verified(archive, headers, cache, directory, folder):
    """Verify raw HTTP length/MD5 and ZIP paths before publishing a new cache directory."""
    if not re.fullmatch(r'chromium(?:_headless_shell)?-[0-9]+', directory):
        raise ValueError('Invalid pinned cache directory')
    if folder not in ('chrome-win64', 'chrome-headless-shell-win64'):
        raise ValueError('Unsupported archive layout')
    cache = Path(cache).resolve()
    destination = cache / directory
    if destination.exists() or destination.is_symlink():
        raise ValueError('Existing browser cache cannot be replaced')
    payload = Path(archive).read_bytes()
    text = Path(headers).read_text(encoding='utf-8')
    lengths = re.findall(r'^Content-Length:\s*(\d+)\s*$', text, re.MULTILINE | re.IGNORECASE)
    digests = re.findall(r'^x-goog-hash:\s*md5=([A-Za-z0-9+/=]+)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if not lengths or not digests or not re.search(r'^HTTP/\S+ 200\b', text, re.MULTILINE):
        raise ValueError('Expected saved official HTTP 200 length and MD5 headers')
    if len(payload) != int(lengths[-1]) or md5(payload).digest() != base64.b64decode(digests[-1], validate=True):
        raise ValueError('Archive differs from the saved official response')
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            name = item.filename.rstrip('/')
            if (not name or '\\' in name or any(p in ('', '.', '..') for p in name.split('/'))
                    or not name.startswith(folder + '/') and name != folder
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError('Unsafe or unexpected ZIP member: ' + name)
            target = (destination / name).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('ZIP member escapes destination')
        cache.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.browser-install-', dir=cache)).resolve()
        try:
            if stage.parent != cache:
                raise ValueError('Staging directory escapes cache')
            zipped.extractall(stage)
            executable = stage / folder / ('chrome.exe' if folder == 'chrome-win64' else 'chrome-headless-shell.exe')
            if not executable.is_file():
                raise ValueError('Archive lacks the pinned browser executable')
            # Playwright's installation marker; dependency validation is still left to Playwright.
            (stage / 'INSTALLATION_COMPLETE').write_bytes(b'')
            if destination.exists():
                raise ValueError('Destination appeared during installation')
            stage.rename(destination)
            return {'directory': directory, 'archiveBytes': len(payload),
                    'archiveSha256': sha256(payload).hexdigest(),
                    'archiveMd5': digests[-1],
                    'executableSha256': sha256((destination / folder / executable.name).read_bytes()).hexdigest()}
        finally:
            if stage.exists() and stage.parent == cache:
                shutil.rmtree(stage)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--downloads-dir', type=Path, required=True)
    cli.add_argument('--node', default=shutil.which('node'))
    cli.add_argument('--report', type=Path, required=True)
    args = cli.parse_args()
    if os.name != 'nt':
        cli.error('This fallback supports only the pinned Windows win64 archives')
    if not args.report.resolve().is_relative_to((ROOT / 'artifacts').resolve()):
        cli.error('Save reports inside artifacts')
    packet = {'scope': 'pinned-browser-archive-install', 'status': 'RUNNING', 'installed': [],
              'nativeExecution': 'NOT_RUN', 'releaseReady': False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write = lambda: args.report.write_text(json.dumps(packet, indent=2) + '\n', encoding='utf-8', newline='\n')
    write()
    try:
        code = "const fs=require('fs'),p=require('path');const base=p.dirname(require.resolve('playwright-core/package.json'));console.log(JSON.stringify({browsers:JSON.parse(fs.readFileSync(p.join(base,'browsers.json'),'utf8')).browsers,executable:require('playwright').chromium.executablePath()}));"
        process = subprocess.run([args.node, '-e', code], cwd=ROOT, capture_output=True,
                                 text=True, timeout=20, check=True)
        metadata = json.loads(process.stdout)
        cache = Path(metadata['executable']).parent.parent.parent.resolve()
        expected_cache = (Path(os.environ['LOCALAPPDATA']) / 'ms-playwright').resolve()
        if cache != expected_cache:
            raise ValueError('Custom browser cache is not supported by this fallback')
        for name, prefix, folder, archive in (
                ('chromium', 'chromium', 'chrome-win64', 'alternate-chromium'),
                ('chromium-headless-shell', 'chromium_headless_shell', 'chrome-headless-shell-win64', 'alternate-headless')):
            browser = next(b for b in metadata['browsers'] if b['name'] == name)
            version = browser['browserVersion']
            receipt = extract_verified(args.downloads_dir / (archive + '.zip'),
                                       args.downloads_dir / (archive + '.headers'), cache,
                                       prefix + '-' + browser['revision'], folder)
            receipt.update(browserVersion=version,
                           sourceUrl=f'https://chrome-for-testing-public.storage.googleapis.com/{version}/win64/{folder}.zip')
            packet['installed'].append(receipt)
            write()
        packet['status'] = 'PASS'
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        packet['status'] = 'FAIL'
        packet['issues'] = [str(exc)]
    write()
    print(json.dumps(packet))
    return 0 if packet['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
