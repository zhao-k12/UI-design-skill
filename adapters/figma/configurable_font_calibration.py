"""Unadmitted source-bound diagnostics for mixed-font Table calibration."""
from decimal import Decimal
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.figma.outline_geometry import inspect_capture
from adapters.figma.font_outline_comparison import compare_six_digit_serialization


class ExactCubicPen(BasePen):
    """Elevate each quadratic exactly; never approximate or fit a curve."""
    def __init__(self, glyphs, cursor, factor):
        super().__init__(glyphs)
        self.cursor=Fraction(cursor);self.factor=Fraction(factor);self.commands=[]

    def point(self,p):
        return ((Fraction(p[0])+self.cursor)*self.factor,-Fraction(p[1])*self.factor)

    def append(self,operation,*points):
        self.commands.append((operation,tuple(self.point(p) for p in points)))

    def _moveTo(self,p): self.append('moveTo',p)
    def _lineTo(self,p): self.append('lineTo',p)
    def _curveToOne(self,a,b,c): self.append('curveTo',a,b,c)
    def _qCurveToOne(self,control,end):
        start=self._getCurrentPoint()
        a=tuple(Fraction(start[i])+Fraction(2,3)*(Fraction(control[i])-Fraction(start[i])) for i in (0,1))
        b=tuple(Fraction(end[i])+Fraction(2,3)*(Fraction(control[i])-Fraction(end[i])) for i in (0,1))
        self.append('curveTo',a,b,end)
    def _closePath(self): self.append('closePath')
    def _endPath(self): raise ValueError('open_font_contour')


def measure(path,digest,characters,size):
    if not characters or len(characters)>128 or any(not ('!'<=c<='~' or '\u4e00'<=c<='\u9fff') for c in characters):
        raise ValueError('unsupported_calibration_text')
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest: raise ValueError('source_font_file_hash_mismatch')
    with TTFont(BytesIO(data),recalcBBoxes=False,recalcTimestamp=False) as font:
        if 'fvar' in font: raise ValueError('variable_font_unresolved')
        glyphs=font.getGlyphSet();cmap=font.getBestCmap();upem=font['head'].unitsPerEm
        cursor=0;commands=[]
        for char in characters:
            name=cmap.get(ord(char))
            if name is None: raise ValueError('source_glyph_missing')
            pen=ExactCubicPen(glyphs,cursor,Fraction(str(size))/upem);glyphs[name].draw(pen)
            commands.extend(pen.commands);cursor+=glyphs[name].width
        # Decimal conversion follows exact degree elevation; SVG has six significant digits.
        values=[(op,tuple(tuple(Decimal(p.numerator)/Decimal(p.denominator) for p in point) for point in points)) for op,points in commands]
        return values,float(Fraction(cursor)*Fraction(str(size))/upem)


def inspect(capture,font_files):
    inspect_capture(capture)
    rows=[]
    for observation in capture['observations']:
        family=observation['fontName']['family']
        if observation['fontName']!={'family':family,'style':'Regular'} or observation['fontSize']!=14 or observation['lineHeight']!={'unit':'PIXELS','value':21}:
            raise ValueError('unsupported_calibration_typography')
        binding=font_files[family]
        source,advance=measure(binding['path'],binding['sha256'],observation['characters'],14)
        paths=list(ET.fromstring(observation['svg']));native=RecordingPen()
        for path in paths: parse_path(path.attrib['d'],native)
        comparison=compare_six_digit_serialization(source,native.value,native_fill_rule=paths[0].get('fill-rule','nonzero') if len(paths)==1 else 'UNRESOLVED',native_path_count=len(paths))
        rows.append({'textReference':observation['textReference'],'characters':observation['characters'],'fontFamily':family,'sourceFontSha256':binding['sha256'],'sourceUnshapedAdvancePx':advance,'nativeWidth':observation['absoluteBounds']['width'],'contourEncoding':comparison})
    return {'scope':'mixed_font_calibration_diagnostic','status':'OBSERVED','observations':rows,'admissionEligible':False,'fidelityGate':'NOT_RUN','limitations':['Unshaped cmap/hmtx positions must be independently compared to actual source layout.','Encoding observations do not authorize tolerance changes or native PNG admission.']}
