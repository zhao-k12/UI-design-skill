import copy
import unittest
from adapters.penpot.configurable_table_instance_qa import validate,META
from validators.ui_ir import load_json


class PenpotTableInstances(unittest.TestCase):
    def test_actual_instances_and_corruption(self):
        for case in ('two-column','four-column'):
            receipt=load_json(META/(case+'-instance-after-placement.json'))
            self.assertEqual(validate(receipt,case)['status'],'PASS')
            for key,value in [('componentReference','wrong'),('mainReference','wrong')]:
                altered=copy.deepcopy(receipt);altered['result'][key]=value
                with self.assertRaises(ValueError):validate(altered,case)
            altered=copy.deepcopy(receipt);altered['result']['instanceNodes'][1]['width']+=1
            with self.assertRaises(ValueError):validate(altered,case)
            altered=copy.deepcopy(receipt);altered['result']['instancePngBase64']=altered['result']['instancePngBase64'][:-4]+'AAAA'
            with self.assertRaises(ValueError):validate(altered,case)

    def test_initial_overlap_cannot_pass_final_canvas_review(self):
        for case in ('two-column','four-column'):
            with self.assertRaisesRegex(ValueError,'instance_canvas_overlap'):
                validate(load_json(META/(case+'-instance-before-placement.json')),case)
