"""Small synthetic SFNT fixtures verify bounds/identity without installing fonts."""
from importlib import import_module
from pathlib import Path
import struct
import tempfile
import unittest

font_identity=import_module('component-builder.source-reader.font_identity')


def name_table(family='FixtureFamily',style='Regular',post='FixtureFamily-Regular',version=0):
    rows=[];storage=b''
    for name_id,value in [(1,family),(2,style),(6,post)]:
        raw=value.encode('utf-16-be')
        rows.append(struct.pack('>HHHHHH',3,1,0x409,name_id,len(raw),len(storage)));storage+=raw
    extra=struct.pack('>H',0) if version==1 else b''
    return struct.pack('>HHH',version,len(rows),6+12*len(rows)+len(extra))+b''.join(rows)+extra+storage


def sfnt(name,offset=0):
    return b'OTTO'+struct.pack('>HHHH',1,0,0,0)+struct.pack('>4sIII',b'name',0,offset+28,len(name))+name


class FontIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'fixture.otf'
        self.path.write_bytes(sfnt(name_table()))

    def test_exact_named_style_and_hash_are_read(self):
        metadata=font_identity.read_font_identity(self.path)
        self.assertEqual(metadata['faces'][0]['namePairs'],[{'family':'FixtureFamily','style':'Regular','postScriptName':'FixtureFamily-Regular'}])
        self.assertEqual(len(metadata['sha256']),64)
        self.assertFalse(metadata['faces'][0]['hasVariableAxes'])

    def test_collection_uses_absolute_table_offsets(self):
        first=sfnt(name_table(),offset=20)
        self.path.write_bytes(b'ttcf'+struct.pack('>III',0x10000,1,20)+b'\0'*4+first)
        metadata=font_identity.read_font_identity(self.path)
        self.assertEqual(metadata['container'],'ttcf');self.assertEqual(metadata['faces'][0]['faceIndex'],0)

    def test_truncated_table_directory_and_string_bounds_fail(self):
        for data in (b'OTTO',sfnt(name_table())[:20],b'wOF2'+b'\0'*30):
            self.path.write_bytes(data)
            with self.assertRaises(ValueError):font_identity.read_font_identity(self.path)
        bad=bytearray(name_table());struct.pack_into('>H',bad,16,65535)
        self.path.write_bytes(sfnt(bytes(bad)))
        with self.assertRaisesRegex(ValueError,'out_of_bounds'):font_identity.read_font_identity(self.path)

    def test_v1_language_table_is_bounded_and_unknown_language_is_rejected(self):
        self.path.write_bytes(sfnt(name_table(version=1)))
        self.assertEqual(font_identity.read_font_identity(self.path)['faces'][0]['nameTableVersion'],1)
        bad=bytearray(name_table(version=1));struct.pack_into('>H',bad,10,0x8000)
        self.path.write_bytes(sfnt(bytes(bad)))
        with self.assertRaisesRegex(ValueError,'language_tag_unknown'):font_identity.read_font_identity(self.path)

    def evidence(self):
        return {'scope':'official_runtime_font_diagnostic','status':'PASS','referenceComponentIrSha256':'fixture',
            'observations':[{'fonts':[{'familyName':'FixtureFamily','postScriptName':'FixtureFamily-Regular','isCustomFont':False,'glyphCount':2}]}]}

    def test_name_match_is_only_a_probe_hint_not_native_binding_or_render_proof(self):
        report=font_identity.correlate_fonts(self.evidence(),[{'path':self.path,'role':'system-file-candidate'}])
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['requirements'][0]['fontNameForLoadProbe'],{'family':'FixtureFamily','style':'Regular'})
        self.assertFalse(report['admissionEligible']);self.assertEqual(report['nativeExecution'],'NOT_RUN')

    def test_unmatched_or_ambiguous_identity_stays_review(self):
        evidence=self.evidence();evidence['observations'][0]['fonts'][0]['postScriptName']='different'
        self.assertEqual(font_identity.correlate_fonts(evidence,[{'path':self.path,'role':'system-file-candidate'}])['status'],'REVIEW')
        duplicate=Path(self.temp.name)/'duplicate.otf';duplicate.write_bytes(self.path.read_bytes())
        report=font_identity.correlate_fonts(self.evidence(),[{'path':path,'role':'system-file-candidate'} for path in (self.path,duplicate)])
        self.assertEqual(report['status'],'REVIEW');self.assertIsNone(report['requirements'][0]['fontNameForLoadProbe'])
        with self.assertRaisesRegex(ValueError,'duplicate_font_input'):
            font_identity.correlate_fonts(self.evidence(),[{'path':self.path,'role':'system-file-candidate'}]*2)
