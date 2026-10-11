"""Hash-bound comparison of a requested font asset and its release sibling.

Only the requested glyph is certified; this does not certify native rendering.
"""
import hashlib
from io import BytesIO
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen


def compare_served_glyph(manifest, served_path, served_hash, sibling_path, sibling_hash,
                         *, resource_path='/vendor/styles/fonts/ionicons.woff2', codepoint=0xf116):
    records=[row for row in manifest.get('servedResources',[]) if row.get('path')==resource_path]
    if not records or any(row.get('sha256')!=served_hash for row in records):
        raise ValueError('served_resource_hash_unverified')
    if isinstance(codepoint,bool) or codepoint!=0xf116:
        raise ValueError('unsupported_glyph_scope')
    snapshots=[]
    for path,digest in ((served_path,served_hash),(sibling_path,sibling_hash)):
        path=Path(path)
        if path.stat().st_size>64*1024*1024:raise ValueError('font_file_too_large')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('font_file_hash_mismatch')
        with TTFont(BytesIO(data),lazy=False,recalcBBoxes=False,recalcTimestamp=False) as font:
            if 'fvar' in font:raise ValueError('variable_font_unsupported')
            name=font.getBestCmap().get(codepoint)
            if name is None:raise ValueError('glyph_missing')
            glyphs=font.getGlyphSet();pen=DecomposingRecordingPen(glyphs);glyphs[name].draw(pen)
            glyph=font['glyf'][name]
            if glyph.isComposite():raise ValueError('composite_hinting_unresolved')
            instructions=bytes(glyph.program.getBytecode()) if hasattr(glyph,'program') else b''
            snapshots.append({'unitsPerEm':font['head'].unitsPerEm,
                'metrics':font['hmtx'][name], 'commands':pen.value,
                'glyphInstructions':instructions,
                'globalHinting':{tag:font.getTableData(tag) if tag in font else None for tag in ('fpgm','prep','cvt ','gasp')}})
    checks={key:snapshots[0][key]==snapshots[1][key] for key in snapshots[0]}
    return {'scope':'served_ionicons_default_arrow_equivalence','status':'PASS' if all(checks.values()) else 'FAIL',
        'codepoint':'U+F116','servedResource':resource_path,'servedSha256':served_hash,
        'siblingSha256':sibling_hash,'checks':checks,'commandCount':len(snapshots[0]['commands']),
        'glyphInstructionBytes':len(snapshots[0]['glyphInstructions']),
        'admissionEligible':False,
        'limitations':['Only U+F116 is compared; other glyphs are unverified.',
            'Native uploaded-file bytes, hinting execution and pixel fidelity are not certified.']}
