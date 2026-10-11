"""Strict source glyph, advance and hint checks on actual embedded CID TrueType."""
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from io import BytesIO
import re
from fontTools.ttLib import TTFont


def unicode_mapping(cmap):
    result={}
    def add(cid,unicode):
        if cid in result or not 0<=cid<=65535 or not 0<unicode<65536:raise ValueError('ambiguous_cid_unicode_mapping')
        result[cid]=chr(unicode)
    for count,body in re.findall(r'(\d+) beginbfchar\s*([\s\S]*?)\s*endbfchar',cmap):
        entries=re.findall(r'<([0-9a-fA-F]{4})>\s*<([0-9a-fA-F]{4})>',body)
        if len(entries)!=int(count) or re.sub(r'<[0-9a-fA-F]{4}>\s*<[0-9a-fA-F]{4}>','',body).strip():raise ValueError('unsupported_cid_bfchar')
        for cid,value in entries:add(int(cid,16),int(value,16))
    for count,body in re.findall(r'(\d+) beginbfrange\s*([\s\S]*?)\s*endbfrange',cmap):
        entries=re.findall(r'<([0-9a-fA-F]{4})>\s*<([0-9a-fA-F]{4})>\s*<([0-9a-fA-F]{4})>',body)
        if len(entries)!=int(count) or re.sub(r'<[0-9a-fA-F]{4}>\s*<[0-9a-fA-F]{4}>\s*<[0-9a-fA-F]{4}>','',body).strip():raise ValueError('unsupported_cid_bfrange')
        for a,b,start in entries:
            a,b,start=map(lambda v:int(v,16),(a,b,start))
            if not 0<=b-a<=256:raise ValueError('unsupported_cid_range_size')
            for cid in range(a,b+1):add(cid,start+cid-a)
    if not result or len(result)>256:raise ValueError('unsupported_cid_inventory')
    return result


def widths(descendant):
    values=descendant.get('/W',[]);result={};i=0
    while i<len(values):
        start=int(values[i]);i+=1;item=values[i];i+=1
        if isinstance(item,list):
            for offset,value in enumerate(item):result[start+offset]=Decimal(str(value))
        else:
            end=int(item);value=Decimal(str(values[i]));i+=1
            if not 0<=end-start<=65535:raise ValueError('invalid_cid_width_range')
            for cid in range(start,end+1):result[cid]=value
    return result,Decimal(str(descendant.get('/DW',1000)))


def compare_embedded_truetype(pdf_path,source_path,source_hash,characters):
    from pypdf import PdfReader
    source_data=source_path.read_bytes()
    if sha256(source_data).hexdigest()!=source_hash:raise ValueError('source_font_hash_mismatch')
    reader=PdfReader(BytesIO(pdf_path.read_bytes()))
    if len(reader.pages)!=1:raise ValueError('expected_one_pdf_page')
    fonts=[(str(key),ref.get_object()) for key,ref in reader.pages[0]['/Resources']['/Font'].items() if ref.get_object()['/Subtype']=='/Type0']
    if len(fonts)!=1:raise ValueError('expected_one_cid_font')
    resource,font=fonts[0]
    if font['/Encoding']!='/Identity-H' or len(font['/DescendantFonts'])!=1:raise ValueError('unsupported_cid_font_encoding')
    descendant=font['/DescendantFonts'][0].get_object();descriptor=descendant['/FontDescriptor'].get_object()
    if descendant['/Subtype']!='/CIDFontType2' or descendant['/CIDToGIDMap']!='/Identity':raise ValueError('unsupported_cid_glyph_mapping')
    mapping=unicode_mapping(font['/ToUnicode'].get_data().decode('ascii'))
    if set(mapping.values())!=set(characters) or len(set(mapping.values()))!=len(mapping):raise ValueError('cid_text_inventory_mismatch')
    embedded=descriptor['/FontFile2'].get_data();metrics,default=widths(descendant);rows=[]
    with TTFont(BytesIO(source_data),recalcBBoxes=False,recalcTimestamp=False) as source,TTFont(BytesIO(embedded),recalcBBoxes=False,recalcTimestamp=False) as actual:
        postscript=source['name'].getDebugName(6)
        if any(re.sub(r'^[A-Z]{6}\+','',str(name).lstrip('/'))!=postscript for name in [font['/BaseFont'],descendant['/BaseFont'],descriptor['/FontName']]):raise ValueError('embedded_font_identity_mismatch')
        if source['head'].unitsPerEm!=actual['head'].unitsPerEm or 'fvar' in source or 'fvar' in actual:raise ValueError('embedded_font_units_mismatch')
        hints={}
        for name in ('fpgm','prep','cvt ','gasp'):
            equal=name in source and name in actual and source.getTableData(name)==actual.getTableData(name)
            hints[name]=equal
        if not all(hints.values()):raise ValueError('embedded_font_hint_tables_mismatch')
        cmap=source.getBestCmap();order=actual.getGlyphOrder();upem=source['head'].unitsPerEm
        for cid,char in sorted(mapping.items()):
            if cid>=len(order) or ord(char) not in cmap:raise ValueError('embedded_glyph_missing')
            original_name=cmap[ord(char)];native_name=order[cid];a=source['glyf'][original_name];b=actual['glyf'][native_name]
            if a.isComposite() or b.isComposite():raise ValueError('unsupported_composite_cid_glyph')
            coords_a,end_a,flags_a=a.getCoordinates(source['glyf']);coords_b,end_b,flags_b=b.getCoordinates(actual['glyf'])
            same=(list(coords_a),list(end_a),list(flags_a),a.numberOfContours)==(list(coords_b),list(end_b),list(flags_b),b.numberOfContours)
            same_hint=a.program.getBytecode()==b.program.getBytecode()
            same_metrics=source['hmtx'][original_name]==actual['hmtx'][native_name]
            expected=(Decimal(source['hmtx'][original_name][0])*1000/Decimal(upem)).quantize(Decimal('.00001'),rounding=ROUND_HALF_UP)
            same_width=metrics.get(cid,default)==expected
            rows.append({'character':char,'cid':cid,'sourceGlyph':original_name,'nativeGlyph':native_name,'orderedCoordinatesFlagsContoursEqual':same,'instructionsEqual':same_hint,'advanceAndBearingEqual':same_metrics,'pdfWidthSerializationEqual':same_width,'status':'PASS' if same and same_hint and same_metrics and same_width else 'FAIL'})
    return {'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','scope':'actual-embedded-cid-truetype-glyphs','resource':resource,'sourceFontSha256':source_hash,'embeddedFontSha256':sha256(embedded).hexdigest(),'nativePdfSha256':sha256(pdf_path.read_bytes()).hexdigest(),'unitsPerEm':upem,'fontHintTablesEqual':hints,'glyphs':rows,'admissionEligible':False}
