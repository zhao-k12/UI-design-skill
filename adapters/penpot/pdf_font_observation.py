"""Read embedded PDF font identities; never substitute PDF for native PNG QA.

Uses optional pypdf (available in the desktop document runtime).
"""
import hashlib
import re


def observe_pdf_fonts(path, expected_postscript_name):
    from pypdf import PdfReader
    reader = PdfReader(path)
    observations = []
    for page_index, page in enumerate(reader.pages):
        fonts = page['/Resources'].get('/Font', {})
        for key, reference in fonts.items():
            font = reference.get_object()
            descriptor = font.get('/FontDescriptor')
            type3 = str(font.get('/Subtype', '')) == '/Type3'
            name = str(font.get('/BaseFont', '') or (descriptor.get_object().get('/FontName', '') if descriptor else '')).lstrip('/')
            normalized = re.sub(r'^[A-Z]{6}\+', '', name)
            descendants = font.get('/DescendantFonts', [font])
            embedded = []
            for item in descendants:
                descriptor = item.get_object().get('/FontDescriptor')
                if descriptor is None:
                    continue
                descriptor = descriptor.get_object()
                for field in ('/FontFile', '/FontFile2', '/FontFile3'):
                    stream = descriptor.get(field)
                    if stream is not None:
                        data = stream.get_object().get_data()
                        embedded.append({'field': field, 'sha256': hashlib.sha256(data).hexdigest(),
                                         'bytes': len(data), 'subtype': str(stream.get_object().get('/Subtype', ''))})
            vectors = []
            if type3:
                for glyph_name, stream in font.get('/CharProcs', {}).items():
                    data = stream.get_object().get_data()
                    vectors.append({'glyphName':str(glyph_name), 'bytes':len(data),
                                    'sha256':hashlib.sha256(data).hexdigest()})
            observations.append({'page': page_index, 'resource': str(key), 'baseFont': name,
                                 'postscriptName': normalized, 'embedded': embedded,
                                 'subtype':str(font.get('/Subtype', '')), 'nativeGlyphStreams':vectors})
    names = {font['postscriptName'] for font in observations}
    issues = []
    if names != {expected_postscript_name}:
        issues.append({'code': 'native_pdf_font_mismatch', 'expected': expected_postscript_name,
                       'observed': sorted(names)})
    if not observations or any(not font['embedded'] and not font['nativeGlyphStreams'] for font in observations):
        issues.append({'code': 'native_pdf_embedded_font_missing'})
    return {'status': 'FAIL' if issues else 'OBSERVED', 'evidenceKind': 'native-pdf-font-observation',
            'pdfSha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'fonts': observations,
            'issues': issues, 'admissionEligible': False, 'glyphGeometryVerified': False,
            'nativePngVerified': False}
