from pathlib import Path
import json
import shutil
import tempfile
import unittest
from scripts.finalize_pipeline import finalize

ROOT=Path(__file__).resolve().parents[1]

class PipelineReleaseTests(unittest.TestCase):
    def test_real_dual_platform_evidence_passes_all_release_gates(self):
        report=finalize(ROOT/'examples/end-to-end-acceptance',ROOT/'examples/acceptance-prototype',ROOT/'adapters/figma/metadata/pipeline-acceptance',ROOT/'adapters/penpot/metadata/pipeline-acceptance')
        self.assertTrue(report['v01Ready']);self.assertTrue(all(report['releaseGates'].values()))
    def test_modified_checkpoint_cannot_reuse_successful_native_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'run';shutil.copytree(ROOT/'examples/end-to-end-acceptance',target)
            (target/'layout_stage.json').write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checkpoint bytes'):
                finalize(target,ROOT/'examples/acceptance-prototype',ROOT/'adapters/figma/metadata/pipeline-acceptance',ROOT/'adapters/penpot/metadata/pipeline-acceptance')

if __name__=='__main__':unittest.main()
