"""Relocate a font-file path only when its raw bytes exactly match saved identity evidence."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def relocate(identity, font, family):
    if identity.get('scope') != 'source_font_file_metadata' or identity.get('status') != 'PASS':
        raise ValueError('A passed font metadata identity is required')
    rows = [r for r in identity['requirements'] if r['familyName'] == family]
    if len(rows) != 1 or len(rows[0]['matches']) != 1:
        raise ValueError('Exactly one family/file match is required')
    match = rows[0]['matches'][0]
    font = Path(font).resolve()
    if sha256(font.read_bytes()).hexdigest() != match['fileSha256']:
        raise ValueError('Font bytes differ from saved identity; substitution is forbidden')
    updated = deepcopy(identity)
    old = match['path']
    for row in updated['requirements']:
        for item in row['matches']:
            if item['path'] == old and item['fileSha256'] == match['fileSha256']:
                item['path'] = str(font)
    for item in updated['files']:
        if item['path'] == old and item['sha256'] == match['fileSha256']:
            item['path'] = str(font)
    updated['pathRelocation'] = {'family': family, 'fileSha256': match['fileSha256'],
                                'rawFontBytesUnchanged': True, 'nativeAcceptance': 'NOT_RUN'}
    return updated


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--identity', type=Path, required=True)
    cli.add_argument('--font', type=Path, required=True)
    cli.add_argument('--family', required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'artifacts').resolve()) or output.exists():
        cli.error('Use a new file inside artifacts')
    try:
        raw = args.identity.read_bytes()
        result = relocate(json.loads(raw.decode('utf-8')), args.font, args.family)
        result['pathRelocation']['originalIdentitySha256'] = sha256(raw).hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8', newline='\n') as saved:
            saved.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result['pathRelocation']))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Font relocation blocked: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
