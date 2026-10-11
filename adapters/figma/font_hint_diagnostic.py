"""Read actual font hint data; do not simulate any rasterizer's hint execution."""
import hashlib
from io import BytesIO
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.misc.psCharStrings import T2OutlineExtractor
from fontTools.pens.recordingPen import RecordingPen

OPERATORS=('hstem','vstem','hstemhm','vstemhm','hintmask','cntrmask','callsubr','callgsubr')
PRIVATE_HINT_KEYS=('BlueValues','OtherBlues','FamilyBlues','FamilyOtherBlues','BlueScale','BlueShift',
    'BlueFuzz','StdHW','StdVW','StemSnapH','StemSnapV','ForceBold','LanguageGroup','ExpansionFactor')


class HintObserver(T2OutlineExtractor):
    def __init__(self,*args,**kwargs):
        self.observed={name:0 for name in OPERATORS};self.executions=0
        super().__init__(*args,**kwargs)

    def execute(self,charstring):
        self.executions+=1
        if self.executions>4096 or len(self.callingStack)>64:raise ValueError('cff_hint_subroutine_limit')
        return super().execute(charstring)

    def observe(self,name,index):
        self.observed[name]+=1
        return getattr(super(),'op_'+name)(index)

    def op_hstem(self,index):return self.observe('hstem',index)
    def op_vstem(self,index):return self.observe('vstem',index)
    def op_hstemhm(self,index):return self.observe('hstemhm',index)
    def op_vstemhm(self,index):return self.observe('vstemhm',index)
    def op_hintmask(self,index):return self.observe('hintmask',index)
    def op_cntrmask(self,index):return self.observe('cntrmask',index)
    def op_callsubr(self,index):return self.observe('callsubr',index)
    def op_callgsubr(self,index):return self.observe('callgsubr',index)


def inspect_font_hints(path,expected_hash,text):
    if not isinstance(text,str) or not text or len(text)>128 or any(not(0x4e00<=ord(char)<=0x9fff or char=='\uf116') for char in text):raise ValueError('unsupported_hint_text_scope')
    path=Path(path)
    if path.stat().st_size>64*1024*1024:raise ValueError('hint_font_file_too_large')
    data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if digest!=expected_hash:raise ValueError('hint_font_hash_mismatch')
    with TTFont(BytesIO(data),lazy=False,recalcBBoxes=False,recalcTimestamp=False) as font:
        if 'fvar' in font or 'CFF2' in font:raise ValueError('variable_hint_instance_unsupported')
        format='CFF_TYPE2' if 'CFF ' in font else 'TRUETYPE' if 'glyf' in font else None
        if format is None:raise ValueError('hint_outline_format_unsupported')
        rows=[]
        for char in dict.fromkeys(text):
            name=font.getBestCmap().get(ord(char))
            if name is None:raise ValueError('hint_glyph_missing')
            row={'character':char,'codepoint':f'U+{ord(char):04X}','glyphName':name}
            if format=='CFF_TYPE2':
                charstring=font['CFF '].cff.topDictIndex[0].CharStrings[name];private=charstring.private
                observer=HintObserver(RecordingPen(),getattr(private,'Subrs',[]),charstring.globalSubrs,
                    private.nominalWidthX,private.defaultWidthX,private)
                observer.execute(charstring)
                row.update(operatorCounts=observer.observed,stemHintCount=observer.hintCount,
                    explicitPrivateHintValues={key:getattr(private,key) for key in PRIVATE_HINT_KEYS if key in private.rawDict},
                    subroutineExecutions=observer.executions-1)
            else:
                glyph=font['glyf'][name]
                if glyph.isComposite():raise ValueError('composite_hint_dependencies_unsupported')
                instructions=bytes(glyph.program.getBytecode()) if hasattr(glyph,'program') else b''
                row.update(instructionBytes=len(instructions),instructionSha256=hashlib.sha256(instructions).hexdigest())
            rows.append(row)
        tables={}
        for tag in ('fpgm','prep','cvt ','gasp'):
            raw=font.getTableData(tag) if tag in font else None
            tables[tag]={'present':raw is not None,'bytes':len(raw) if raw is not None else 0,
                'sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None}
        return {'scope':'source_font_hint_data_diagnostic','status':'REVIEW','fontFileSha256':digest,
            'outlineFormat':format,'glyphs':rows,'globalHintTables':tables,
            'admissionEligible':False,'fidelityGate':'NOT_RUN',
            'limitations':['CFF observation expands subroutines for operator/data inspection, without executing grid fitting.',
                'No glyph-local hints does not exclude private hint parameters, automatic hinting or engine-specific rasterization.',
                'Font data does not establish which hints the browser or Figma applies.']}
