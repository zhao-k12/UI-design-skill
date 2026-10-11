from copy import deepcopy
from importlib import import_module
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from adapters.figma.list_acceptance import run
from validators.ui_ir import ROOT,load_json


class Task009AcceptanceTests(unittest.TestCase):
    def test_actual_list_has_six_instances_and_unchanged_admitted_pixels(self):
        report=run(ROOT/'adapters/figma/metadata',ROOT/'artifacts/task-009/list-acceptance')
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['nativeInstances'],6)
        self.assertEqual(report['screenshotDimensions'],[1440,496]);self.assertTrue(all(r['changedPixels']==0 for r in report['instanceRasterComparisons']))

    def test_flattened_instance_and_changed_text_are_rejected_by_independent_readback(self):
        for field,value in [('type','FRAME'),('mainComponentReference','wrong')]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                metadata=Path(temporary)/'metadata';shutil.copytree(ROOT/'adapters/figma/metadata',metadata)
                path=metadata/'list-independent-readback.json';readback=load_json(path)
                next(r for r in readback['evidence'] if r['uiIrId']=='table.body')[field]=value
                path.write_text(json.dumps(readback),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'independent_property_mismatch'):run(metadata,ROOT/'artifacts/task-009/list-acceptance')

    def test_production_registry_rejects_incomplete_edge_proofs_even_with_rehashed_reports(self):
        module=import_module('core.component-resolver.registry')
        for field,value in [('changedPixelsOutsideEdgeBand',1),('changedPixelsOutsidePermittedRegions',1),('policy','unbounded')]:
            with self.subTest(field=field):
                catalog=load_json(ROOT/'registries/components/catalog.json');reports=load_json(ROOT/'registries/components/fidelity-reports.json')
                entry=catalog['components']['form.input.default.medium'];report=reports[entry['fidelity']['reportId']]
                report['checks']['screenshot'][field]=value;entry['fidelity']['reportSha256']=module.digest(report)
                with self.assertRaises(module.ComponentError):module.ComponentRegistry(catalog,reports)
