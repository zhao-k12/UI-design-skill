from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from adapters.penpot.table_pixel_coverage import compare,REQUIRED_PROOFS
from validators.visual.fidelity import digest,file_hash


class CrossRendererTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.paths=[Path(self.tmp.name)/name for name in ('source.png','native.png','vector.png')]
        for path in self.paths:
            image=Image.new('RGBA',(24,24),'white');draw=ImageDraw.Draw(image)
            draw.rectangle((8,6,9,17),fill='black');draw.rectangle((8,6,15,7),fill='black');image.save(path)
        self.ref={'logicalComponentId':'fixture','componentType':'Button','variant':'default','state':'static',
            'props':{},'content':{'text':'一'},'fixtureContext':{},'provenance':{'sourceVersion':'fixture'},
            'screenshot':{'sha256':file_hash(self.paths[0])}}
        self.candidate={k:deepcopy(self.ref[k]) for k in ('logicalComponentId','variant','state','props','content','fixtureContext')}
        self.candidate.update(scope='test-fixture',normalizationVersion='0.2.0',evidenceKind='native-design-capture',sourceVersion='fixture',componentIrSha256=digest(self.ref),
            verification=dict.fromkeys(REQUIRED_PROOFS,'PASS'),capture={'captureId':'fixture','exporterVersion':'fixture','nativeEvidenceSha256':'1'*64,'proofBundleSha256':'2'*64},
            rasterContext={'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},
            screenshotSha256=file_hash(self.paths[1]),vectorRasterSha256=file_hash(self.paths[2]),
            glyphPaintSamples=[{'characters':'一','region':{'x':6,'y':4,'width':12,'height':16},'advances':[12],'foreground':[0,0,0],'background':[255,255,255]}])

    def check(self):return compare(self.ref,self.candidate,*self.paths,scope='test-fixture')

    def edit(self,xy,color):
        with Image.open(self.paths[1]) as image:image.putpixel(xy,color);image.save(self.paths[1])
        self.candidate['screenshotSha256']=file_hash(self.paths[1])

    def test_fixture_pass_does_not_admit_production(self):
        self.assertEqual(self.check()['status'],'PASS');self.assertFalse(self.check()['admissionEligible'])

    def test_edge_difference_passes_only_with_all_semantic_proofs(self):
        self.edit((8,10),(90,90,90,255));self.assertEqual(self.check()['status'],'PASS')
        for name in REQUIRED_PROOFS:
            with self.subTest(name=name):
                self.candidate['verification'][name]='REVIEW';self.assertEqual(self.check()['status'],'FAIL');self.candidate['verification'][name]='PASS'

    def test_nonedge_changes_fail(self):
        self.edit((22,22),(254,254,254,255));self.assertEqual(self.check()['status'],'FAIL')

    def test_erasing_entire_thin_glyph_cannot_hide_inside_edge_band(self):
        Image.new('RGBA',(24,24),'white').save(self.paths[1]);self.candidate['screenshotSha256']=file_hash(self.paths[1])
        result=self.check();self.assertEqual(result['checks']['screenshot']['changedPixelsOutsideEdgeBand'],0)
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['checks']['glyphRetention'][0]['retentionRatio'],0)

    def test_wrong_content_hash_and_scaled_capture_are_rejected(self):
        self.candidate['content']={'text':'二'};self.assertEqual(self.check()['status'],'FAIL')
        self.candidate['content']=self.ref['content'];self.candidate['screenshotSha256']='0'*64;self.assertEqual(self.check()['status'],'FAIL')
        self.candidate['screenshotSha256']=file_hash(self.paths[1]);self.candidate['rasterContext']['scale']=2;self.assertEqual(self.check()['status'],'FAIL')

    def test_invalid_glyph_regions_are_failure_not_silent_exemption(self):
        self.candidate['glyphPaintSamples'][0]['region']['width']=12.00000001
        self.assertEqual(self.check()['status'],'FAIL')

    def test_fractional_table_box_uses_positive_pixel_area_without_expanding_edge_band(self):
        self.ref['componentType']='Table';self.candidate['componentIrSha256']=digest(self.ref)
        sample=self.candidate['glyphPaintSamples'][0]
        sample['region']={'x':6,'y':4,'width':9.25,'height':16};sample['advances']=[9.25]
        self.edit((15,7),(90,90,90,255))
        self.assertEqual(self.check()['status'],'FAIL') # Frozen center policy.
        self.candidate.update(normalizationVersion='0.2.1',pixelRegionPolicy='positive-area-intersection')
        self.assertEqual(self.check()['status'],'PASS')
        self.edit((16,7),(90,90,90,255));self.assertEqual(self.check()['status'],'FAIL')
        self.edit((22,22),(254,254,254,255));self.assertEqual(self.check()['status'],'FAIL')

    def test_pixel_coverage_requires_table_scope_and_exact_policy(self):
        self.candidate.update(normalizationVersion='0.2.1',pixelRegionPolicy='positive-area-intersection')
        self.assertEqual(self.check()['status'],'FAIL')
        self.ref['componentType']='Table';self.candidate['componentIrSha256']=digest(self.ref)
        self.candidate['pixelRegionPolicy']='rounded-or-expanded-box';self.assertEqual(self.check()['status'],'FAIL')
