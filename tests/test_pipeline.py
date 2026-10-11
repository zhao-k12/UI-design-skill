import copy
import importlib
from pathlib import Path
import tempfile
import unittest
from validators.ui_ir import ROOT,load_json

BASE=ROOT/'examples/acceptance-prototype'
runner=importlib.import_module('core.pipeline.runner')
resolver=importlib.import_module('core.component-resolver.resolver')


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens=resolver.tokens.TokenRegistry(load_json(ROOT/'registries/tokens/default.json'))
        cls.components=resolver.registry_module.ComponentRegistry(load_json(ROOT/'registries/components/catalog.json'),load_json(ROOT/'registries/components/fidelity-reports.json'))
        lock=load_json(ROOT/'registries/icons/current.json')
        cls.icons=importlib.import_module('core.icon-resolver.registry').IconRegistry(load_json(ROOT/'registries/icons/snapshots'/lock['snapshotSha256']/'registry.json'))
        cls.assets=importlib.import_module('core.asset-resolver.registry').AssetRegistry(load_json(ROOT/'registries/assets/catalog.json'),ROOT/'registries/assets')
        cls.geometry=importlib.import_module('core.component-resolver.placement').SourceGeometry(load_json(BASE/'source-geometry.json'),cls.components)
        cls.icon_sources={i:(ROOT/'registries/icons/objects'/(cls.icons.resolve(i)['descriptor']['svgSha256']+'.svg')).read_bytes() for i in ('remix.settings-3-line','remix.download-line')}

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.output=Path(self.temp.name)
        self.inputs={k:load_json(BASE/n) for k,n in [('observations','observations.json'),('review','review.json'),('plan','layout-plan.json'),('decisions','decisions.json'),('content','content.json'),('versions','versions.json'),('measurements','runtime-measurements.json')]}

    def run_pipeline(self):
        i=self.inputs
        return runner.run(i['observations'],BASE,i['review'],i['plan'],i['decisions'],i['content'],self.components,self.tokens,self.icons,self.assets,self.geometry,self.icon_sources,i['versions'],self.output,measurement_evidence=i['measurements'],evidence_root=ROOT)

    def test_actual_approved_source_runs_and_resume_reuses_byte_bound_stages(self):
        qa=self.run_pipeline();self.assertEqual(qa['status'],'PASS',qa)
        self.assertEqual((qa['semanticItemCount'],qa['instanceCount'],qa['iconCount']),(9,4,2))
        self.assertFalse(qa['v01Ready']);self.assertEqual(qa['nativeExecution'],'NOT_RUN')
        resumed=self.run_pipeline();self.assertEqual(resumed['executedStages'],[])
        self.assertEqual(resumed['uiIrSha256'],qa['uiIrSha256']);self.assertEqual(len(resumed['reusedStages']),9)

    def test_mapping_change_resumes_there_and_keeps_unchanged_native_payload(self):
        self.assertEqual(self.run_pipeline()['status'],'PASS')
        self.inputs['decisions']['items'][0]['rationale']+=' Independently checked source.'
        i=self.inputs
        current=runner.mapping_module.resolve(load_json(BASE/'prototype_analysis.json'),load_json(BASE/'page_tree.json'),
            BASE,i['review'],i['plan'],i['decisions'],self.components,self.tokens,allow_text_primitives=True)
        self.inputs['content']['mappingSha256']=runner.builder.fingerprint(current)
        qa=self.run_pipeline();self.assertEqual(qa['status'],'PASS',qa)
        self.assertEqual(qa['executedStages'][0],'component-mapping');self.assertIn('layout',qa['reusedStages'])
        self.assertEqual(load_json(self.output/'assembly.json')['changedSections'],[])

    def test_rejected_review_invalidates_downstream_and_removes_stale_final_document(self):
        self.assertEqual(self.run_pipeline()['status'],'PASS')
        self.inputs['review']['decision']='rejected';qa=self.run_pipeline()
        self.assertEqual(qa['status'],'Review');self.assertEqual(qa['blockedStage'],'structure-qa')
        self.assertIsNone(load_json(self.output/'final_ui_ir.json'))
        self.assertEqual(set(load_json(self.output/'checkpoint.json')['stages']),{'semantic-parse','page-tree'})

    def test_fake_runtime_size_is_rejected_even_if_labeled_runtime(self):
        self.inputs['plan']['measurements']['field-name']['width']+=1
        qa=self.run_pipeline();self.assertEqual(qa['status'],'FAIL');self.assertFalse(qa['readyForAdapter'])

    def test_source_body_cannot_silently_replace_different_static_records(self):
        item=next(i for i in self.inputs['content']['items'] if i['sourceId']=='user-table')
        item['tableRecords'][0]['name']['text']='李四'
        qa=self.run_pipeline();self.assertEqual(qa['status'],'Unsupported');self.assertIsNone(load_json(self.output/'final_ui_ir.json'))

    def test_corrupt_cached_layout_reruns_from_layout_and_version_migration_blocks(self):
        self.assertEqual(self.run_pipeline()['status'],'PASS')
        (self.output/'layout_stage.json').write_text('{}',encoding='utf-8')
        qa=self.run_pipeline();self.assertEqual(qa['status'],'PASS');self.assertEqual(qa['executedStages'][0],'layout')
        self.inputs['versions']['skill_version']='another-release'
        with self.assertRaises(ValueError):self.run_pipeline()

    def test_layout_order_cannot_omit_or_duplicate_source_items(self):
        for kind in ('inline','row'):
            original=copy.deepcopy(self.inputs['plan'])
            if kind=='inline':self.inputs['plan']['sectionConfigs']['query']['inlineOrder']=['field-name']
            else:self.inputs['plan']['sectionConfigs']['list']['contentRows']=[['list-title','list-title']]
            report=self.run_pipeline();self.assertNotEqual('PASS',report['status']);self.assertFalse(report['readyForAdapter'])
            self.inputs['plan']=original

    def test_table_headers_and_source_records_cannot_be_incomplete(self):
        item=next(i for i in self.inputs['content']['items'] if i['sourceId']=='user-table')
        original=copy.deepcopy(item)
        for key in ('headers','tableRecords'):
            item.clear();item.update(copy.deepcopy(original))
            if key=='headers':item['props']['headers'].pop()
            else:item['tableRecords'].pop()
            report=self.run_pipeline();self.assertNotEqual('PASS',report['status']);self.assertFalse(report['readyForAdapter'])
