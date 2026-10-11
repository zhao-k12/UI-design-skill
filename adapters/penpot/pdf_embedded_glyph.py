"""Verify one observed Identity-H CIDFontType2 glyph against its source TTF."""
import hashlib
from io import BytesIO
import re
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen


def require(condition, reason):
    if not condition:raise ValueError(reason)


def compare_embedded_glyph(pdf_path, source_path, source_sha, character, postscript_name):
    from pypdf import PdfReader
    source_bytes=source_path.read_bytes();pdf_bytes=pdf_path.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest()==source_sha,'source_font_hash_mismatch')
    require(isinstance(character,str) and len(character)==1,'unsupported_embedded_glyph_scope')
    reader=PdfReader(BytesIO(pdf_bytes));require(len(reader.pages)==1,'expected_one_component_pdf_page')
    fonts=[(str(k),v.get_object()) for k,v in reader.pages[0]['/Resources']['/Font'].items() if v.get_object()['/Subtype']=='/Type0']
    require(len(fonts)==1,'embedded_font_inventory_mismatch')
    resource,font=fonts[0]
    normalized=lambda value:re.sub(r'^[A-Z]{6}\+','',str(value).lstrip('/'))
    require(normalized(font['/BaseFont'])==postscript_name and font['/Encoding']=='/Identity-H' and len(font['/DescendantFonts'])==1,'unsupported_embedded_font_mapping')
    descendant=font['/DescendantFonts'][0].get_object()
    require(descendant['/Subtype']=='/CIDFontType2' and descendant['/CIDToGIDMap']=='/Identity','unsupported_cid_to_gid_mapping')
    cmap=font['/ToUnicode'].get_object().get_data().decode('ascii')
    mappings=re.findall(r'1 beginbfchar\s*<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]{4})>\s*endbfchar',cmap)
    require(len(mappings)==1 and cmap.count('beginbfchar')==1 and 'beginbfrange' not in cmap,'unsupported_embedded_unicode_mapping')
    cid,unicode_value=(int(v,16) for v in mappings[0]);require(unicode_value==ord(character),'embedded_glyph_content_mismatch')
    descriptor=descendant['/FontDescriptor'].get_object()
    require(normalized(descriptor['/FontName'])==postscript_name and '/FontFile2' in descriptor and '/FontFile3' not in descriptor and '/FontFile' not in descriptor,'unsupported_embedded_font_file')
    font_bytes=descriptor['/FontFile2'].get_object().get_data()
    with TTFont(BytesIO(source_bytes)) as source, TTFont(BytesIO(font_bytes)) as native:
        require('glyf' in native and 'glyf' in source and native['head'].unitsPerEm==source['head'].unitsPerEm,'embedded_font_units_mismatch')
        require(native['name'].getDebugName(6)==source['name'].getDebugName(6)==postscript_name and native['OS/2'].usWeightClass==source['OS/2'].usWeightClass==400,'embedded_font_identity_mismatch')
        native_name=native.getGlyphName(cid);source_name=source.getBestCmap()[ord(character)]
        require(native.getBestCmap().get(ord(character))==native_name,'embedded_font_cmap_mismatch')
        def outline(font,name):
            glyphs=font.getGlyphSet();pen=DecomposingRecordingPen(glyphs);glyphs[name].draw(pen);return pen.value
        expected,observed=outline(source,source_name),outline(native,native_name)
        same=expected==observed;metrics_equal=source['hmtx'][source_name]==native['hmtx'][native_name]
        source_hint=bytes(source['glyf'][source_name].program.getBytecode())
        native_hint=bytes(native['glyf'][native_name].program.getBytecode())
        hint_equal=source_hint==native_hint
        advance=source['hmtx'][source_name][0]
        pdf_width=descendant.get('/DW',1000)
        # This observed one-glyph subset uses only the default CID advance.
        require('/W' not in descendant and pdf_width==advance*1000/source['head'].unitsPerEm,'unsupported_embedded_pdf_advance')
        return {'status':'PASS' if same and metrics_equal and hint_equal else 'FAIL',
            'scope':'observed-embedded-TTF-glyph-in-font-units','nativePdfSha256':hashlib.sha256(pdf_bytes).hexdigest(),
            'sourceFontSha256':source_sha,'embeddedFontSha256':hashlib.sha256(font_bytes).hexdigest(),
            'resource':resource,'character':character,'cid':cid,'postscriptName':postscript_name,
            'unitsPerEm':source['head'].unitsPerEm,'orderedCompleteContoursEqual':same,'advanceAndBearingEqual':metrics_equal,
            'hintInstructionsEqual':hint_equal,'sourceCommandCount':len(expected),'nativeCommandCount':len(observed),
            'advanceFontUnits':advance,'sourceCommands':expected,'nativeCommands':observed,
            'admissionEligible':False,'limitations':['Only the observed glyph is compared; editable content, baseline and native PNG require separate proof.']}
