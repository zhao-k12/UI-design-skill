"""Current real instance/source exports must retain admitted truth and edge bounds."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from adapters.figma.pipeline_fidelity import verify

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_bytes())

class PipelineFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=read('examples/end-to-end-acceptance/figma_preflight.json')['plan']
        base='adapters/figma/metadata/pipeline-acceptance/'
        cls.execution=read(base+'execution.json');cls.capture=read(base+'capture.json')
        cls.packet=read(base+'instances-capture.json');cls.sources=read(base+'current-source-capture.json')
    def test_actual_sources_instances_and_approved_edge_rules(self):
        report=verify(self.plan,self.execution,self.capture,self.packet,self.sources)
        self.assertEqual('PASS',report['status']);self.assertEqual(6,len(report['instances']))
        self.assertTrue(all(n.get('outsideVerifiedEdges',0)==0 for n in report['instances']))
    def test_changed_source_geometry_style_or_glyph_cannot_reuse_admission(self):
        for field in ('geometry','style','glyph'):
            sources=deepcopy(self.sources);s=sources['sources'][0]
            if field=='geometry':s['nativeEvidence']['nodes'][0]['localBounds']['width']+=1
            elif field=='style':s['nativeEvidence']['nodes'][0]['properties']['opacity']=0.5
            else:s['textOutlines'][0]['svg']+=' '
            with self.assertRaises(ValueError):verify(self.plan,self.execution,self.capture,self.packet,sources)
    def test_missing_or_changed_instance_export_and_icon_path_rejected(self):
        for field in ('png','master','icon'):
            packet=deepcopy(self.packet)
            if field=='png':packet['observations'][1]['nativePngBase64']='AAAA'
            elif field=='master':packet['observations'][1]['mainReference']='foreign'
            else:packet['observations'][0]['vectorPaths'][0][0]['data']='M0 0L1 1'
            with self.assertRaises((ValueError,KeyError)):verify(self.plan,self.execution,self.capture,packet,self.sources)

if __name__=='__main__':unittest.main()
