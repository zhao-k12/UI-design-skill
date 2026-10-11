"""Compare actual native PDF Type3 glyph paths with the locked source font.

Only the observed simple CFF path serialization is supported. Unknown PDF
operators, paints, mappings or matrices stop verification rather than normalize
away a difference. Requires optional pypdf plus fontTools.
"""
from decimal import Decimal
import hashlib
from io import BytesIO
import re
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen


def parse_type3_glyph(data):
    commands, width, painted = [], None, False
    for line in data.decode('ascii').splitlines():
        parts = line.split()
        if not parts:
            continue
        op, args = parts[-1], parts[:-1]
        if op == 'd1' and width is None and len(args) == 6:
            values = [Decimal(v) for v in args]
            if values[1] != 0:
                raise ValueError('unsupported_vertical_glyph_advance')
            width = values[0]
        elif op in ('m', 'l', 'c') and not painted:
            expected = {'m': 2, 'l': 2, 'c': 6}[op]
            if len(args) != expected:
                raise ValueError('invalid_pdf_glyph_path')
            values = [Decimal(v) for v in args]
            # Native Type3 FontMatrix reflects y; undo only that known reflection.
            points = tuple((values[i], -values[i+1]) for i in range(0, len(values), 2))
            commands.append(({'m':'moveTo','l':'lineTo','c':'curveTo'}[op], points))
        elif op == 'h' and not args and not painted:
            commands.append(('closePath', ()))
        elif op == 'f' and not args and not painted and commands:
            painted = True
        else:
            raise ValueError('unsupported_pdf_glyph_operator')
    if width is None or not painted or not commands or commands[-1][0] != 'closePath':
        raise ValueError('incomplete_pdf_glyph_path')
    return commands, width


def parse_bfchar_mapping(cmap):
    blocks=re.findall(r'(\d+) beginbfchar\s*([\s\S]*?)\s*endbfchar',cmap)
    if len(blocks)!=1 or cmap.count('beginbfchar')!=1 or 'beginbfrange' in cmap:
        raise ValueError('unsupported_native_unicode_mapping')
    count,body=blocks[0];entries=re.findall(r'<([0-9A-Fa-f]{2})>\s*<([0-9A-Fa-f]{4})>',body)
    if not 0<int(count)<=256 or len(entries)!=int(count) or re.sub(r'<[0-9A-Fa-f]{2}>\s*<[0-9A-Fa-f]{4}>','',body).strip():
        raise ValueError('unsupported_native_unicode_mapping')
    parsed=[(int(code,16),int(value,16)) for code,value in entries]
    if len({code for code,value in parsed})!=len(parsed) or len({value for code,value in parsed})!=len(parsed):
        raise ValueError('ambiguous_native_unicode_mapping')
    return parsed


def extract_type3_glyphs(pdf_path, *, allowed_type0_names=()):
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(pdf_path.read_bytes()))
    if len(reader.pages) != 1:
        raise ValueError('expected_one_component_pdf_page')
    result = []
    for resource, ref in reader.pages[0]['/Resources']['/Font'].items():
        font = ref.get_object()
        if str(font['/Subtype']) != '/Type3':
            name=re.sub(r'^[A-Z]{6}\+', '', str(font.get('/BaseFont','')).lstrip('/'))
            if str(font['/Subtype'])=='/Type0' and name in allowed_type0_names:
                continue
            raise ValueError('unsupported_native_pdf_font_type')
        matrix = [str(v) for v in font['/FontMatrix']]
        # Record the real serializer's matrix; do not claim exact 0.001 scaling.
        if [Decimal(v) for v in matrix] != [Decimal('0.0010000001'),0,0,Decimal('-0.0010000001'),0,0]:
            raise ValueError('unsupported_native_type3_font_matrix')
        cmap = font['/ToUnicode'].get_object().get_data().decode('ascii')
        mappings = parse_bfchar_mapping(cmap)
        names, current = {}, None
        for value in font['/Encoding']['/Differences']:
            if isinstance(value, int):
                current = value
            else:
                if current is None:
                    raise ValueError('invalid_native_font_encoding')
                names[current] = str(value); current += 1
        descriptor = font['/FontDescriptor'].get_object()
        for code,unicode_value in mappings:
            glyph_name = names[code]
            data = font['/CharProcs'][glyph_name].get_object().get_data()
            commands, advance = parse_type3_glyph(data)
            result.append({'resource':str(resource), 'character':chr(unicode_value),
                'nativePdfSha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                'postscriptName':re.sub(r'^[A-Z]{6}\+', '', str(descriptor['/FontName']).lstrip('/')),
                'fontWeight':int(descriptor['/FontWeight']), 'fontMatrix':matrix,
                'glyphName':glyph_name, 'pathSha256':hashlib.sha256(data).hexdigest(),
                'nativeCommands':commands, 'advanceFontUnits':advance})
    return result


def compare_glyphs(source_path, expected_sha256, observations, characters):
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('source_font_hash_mismatch')
    if len(observations) != len(characters) or len(set(characters)) != len(characters):
        raise ValueError('unsupported_glyph_scope')
    hashes = {o.get('nativePdfSha256') for o in observations}
    if len(hashes) != 1 or not re.fullmatch(r'[0-9a-f]{64}', next(iter(hashes)) or ''):
        raise ValueError('native_glyph_document_mismatch')
    results = []
    with TTFont(source_path) as font:
        if font['head'].unitsPerEm != 1000:
            raise ValueError('unsupported_source_font_units')
        glyph_set, cmap = font.getGlyphSet(), font.getBestCmap()
        for ch in characters:
            matches = [o for o in observations if o['character'] == ch]
            # PDF ToUnicode can select a different Unicode alias of the same
            # source glyph (e.g. 入 and Kangxi radical ⼊). This proves glyph
            # identity only; editable content must still be checked separately.
            if not matches:
                matches = [o for o in observations if cmap.get(ord(o['character'])) == cmap.get(ord(ch)) and cmap.get(ord(ch)) is not None]
            if len(matches) != 1:
                raise ValueError('native_glyph_missing_or_ambiguous')
            observed = matches[0]
            if [Decimal(v) for v in observed['fontMatrix']] != [Decimal('0.0010000001'),0,0,Decimal('-0.0010000001'),0,0]:
                raise ValueError('unsupported_native_type3_font_matrix')
            name = cmap[ord(ch)]
            pen = DecomposingRecordingPen(glyph_set); glyph_set[name].draw(pen)
            expected = [(op,tuple((Decimal(str(x)),Decimal(str(y))) for x,y in points)) for op,points in pen.value]
            same = expected == observed['nativeCommands']
            advance = Decimal(str(font['hmtx'][name][0]))
            same_advance = advance == observed['advanceFontUnits']
            same_identity = observed['postscriptName'] == font['name'].getDebugName(6) and observed['fontWeight'] == font['OS/2'].usWeightClass
            results.append({'character':ch, 'pathSha256':observed['pathSha256'],
                'nativeUnicodeCharacter':observed['character'],
                'sourceCmapGlyphAlias':observed['character'] != ch,
                'orderedCompleteContoursEqual':same, 'advanceFontUnitsEqual':same_advance,
                'fontIdentityEqual':same_identity, 'sourceCommandCount':len(expected),
                'nativeCommandCount':len(observed['nativeCommands']), 'fontMatrix':observed['fontMatrix'],
                'status':'PASS' if same and same_advance and same_identity else 'FAIL'})
        return {'status':'PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
                'scope':'observed-Type3-glyph-paths-in-font-units', 'unitsPerEm':font['head'].unitsPerEm,
                'sourceFontSha256':expected_sha256, 'nativePdfSha256':next(iter(hashes)),
                'glyphs':results, 'admissionEligible':False,
                'limitations':['Font-unit contours are exact; the recorded PDF matrix has serializer rounding.',
                    'Unicode aliases are checked against the source cmap; this does not prove editable text content.',
                    'PDF glyph paths do not establish native PNG raster edges or full component fidelity.']}
