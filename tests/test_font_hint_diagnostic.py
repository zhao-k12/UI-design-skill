import hashlib
import unittest
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.cffLib import SubrsIndex
from tests import test_font_outline_comparison as fixtures
from adapters.figma.font_hint_diagnostic import inspect_font_hints


class FontHintTests(unittest.TestCase):
    def setUp(self):fixtures.FontOutlineComparisonTests.setUp(self)

    def inspect(self):return inspect_font_hints(self.path,hashlib.sha256(self.path.read_bytes()).hexdigest(),'一')

    def test_reads_actual_true_type_instruction_bytes_without_running_them(self):
        self.assertEqual(self.inspect()['glyphs'][0]['instructionBytes'],0)
        with TTFont(self.path) as font:
            font['glyf']['fixture'].program=Program();font['glyf']['fixture'].program.fromBytecode([0])
            font.save(self.path)
        report=self.inspect();self.assertEqual(report['glyphs'][0]['instructionBytes'],1)
        self.assertEqual(report['status'],'REVIEW');self.assertFalse(report['admissionEligible'])

    def test_cff_stem_operators_and_private_parameters_are_distinct(self):
        builder=FontBuilder(1000,isTTF=False);builder.setupGlyphOrder(['.notdef','fixture'])
        builder.setupCharacterMap({0x4e00:'fixture'})
        builder.setupHorizontalMetrics({name:(1000,0) for name in ('.notdef','fixture')})
        builder.setupHorizontalHeader(ascent=800,descent=-200)
        builder.setupNameTable({'familyName':'Fixture','styleName':'Regular','psName':'Fixture-Regular'})
        builder.setupOS2();builder.setupPost()
        builder.setupCFF('Fixture-Regular',{}, {'.notdef':T2CharString(program=['endchar']),
            'fixture':T2CharString(program=[20,30,'hstem',0,0,'rmoveto',100,0,0,100,-100,0,'rlineto','endchar'])},
            {'defaultWidthX':1000,'StdHW':30,'StdVW':40})
        builder.save(self.path)
        report=self.inspect();row=report['glyphs'][0]
        self.assertEqual(report['outlineFormat'],'CFF_TYPE2');self.assertEqual(row['operatorCounts']['hstem'],1)
        self.assertEqual(row['stemHintCount'],1);self.assertEqual(row['explicitPrivateHintValues']['StdVW'],40)
        top=builder.font['CFF '].cff.topDictIndex[0];private=top.Private
        private.Subrs=SubrsIndex()
        private.Subrs.append(T2CharString(program=[20,30,'hstem','return'],private=private,
            globalSubrs=builder.font['CFF '].cff.GlobalSubrs))
        top.CharStrings['fixture'].program=[-107,'callsubr',0,0,'rmoveto',100,0,0,100,-100,0,'rlineto','endchar']
        builder.save(self.path)
        row=self.inspect()['glyphs'][0]
        self.assertEqual(row['operatorCounts']['callsubr'],1);self.assertEqual(row['operatorCounts']['hstem'],1)
        self.assertEqual(row['subroutineExecutions'],1);self.assertEqual(row['stemHintCount'],1)

    def test_changed_font_hash_and_missing_glyph_fail(self):
        with self.assertRaisesRegex(ValueError,'hash_mismatch'):inspect_font_hints(self.path,'0'*64,'一')
        with self.assertRaisesRegex(ValueError,'glyph_missing'):inspect_font_hints(self.path,self.digest,'二')
