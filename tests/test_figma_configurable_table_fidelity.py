import copy
import tempfile
from pathlib import Path
import unittest
from adapters.figma.configurable_table_fidelity import evaluate,geometry,outlines,prepare_source,SOURCE,META,transport
from adapters.figma.configurable_table_instance_qa import validate
from validators.ui_ir import ROOT


class FigmaConfigurableTableTests(unittest.TestCase):
    def test_actual_complete_native_gates(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as tmp:
            for case in ('two-column','four-column'):
                report=evaluate(case,Path(tmp)/case)
                self.assertEqual(report['status'],'PASS')
                self.assertEqual(report['checks']['screenshot']['changedPixelsOutsideEdgeBand'],0)

    def test_geometry_content_and_render_corruption(self):
        capture=transport(META/'table-capture-after-sizing-pieces-0.json');observations,arial=outlines();plan=prepare_source(SOURCE/'two-column')
        for field,value in [('fontSize',15),('characters','wrong'),('textAutoResize','NONE'),('opacity',0),('letterSpacing',{'unit':'PIXELS','value':1})]:
            native=copy.deepcopy(capture['nativeEvidence']);text=next(n for n in native['nodes'] if n['type']=='TEXT');text['properties'][field]=value
            with self.assertRaises(ValueError):geometry(native,plan,observations,arial)
        native=copy.deepcopy(capture['nativeEvidence']);native['nodes'][1]['absoluteBounds']['width']+=1
        with self.assertRaises(ValueError):geometry(native,plan,observations,arial)

    def test_actual_linked_instances_and_corruption(self):
        for i,case in enumerate(('two-column','four-column')):
            receipt=transport(META/f'instance-readback-pieces-{i}.json')
            self.assertEqual(validate(receipt,case)['status'],'PASS')
            altered=copy.deepcopy(receipt);altered['instanceNativeCapture']['nativeEvidence']['nodes'][1]['parentReference']='wrong'
            with self.assertRaises(ValueError):validate(altered,case)
            altered=copy.deepcopy(receipt);altered['instanceNativeCapture']['raster']['bytes'][100]^=1
            with self.assertRaises(ValueError):validate(altered,case)
            altered=copy.deepcopy(receipt);altered['mainReference']='wrong'
            with self.assertRaises(ValueError):validate(altered,case)
