"""The production CLI routes all design resources by one explicit profile."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.run_pipeline import profile_resources
from validators.ui_ir import ROOT, load_json


class V02PipelineProfileTests(unittest.TestCase):
    def test_profiles_are_complete_and_separate(self):
        old, new = profile_resources('v0.1'), profile_resources('v0.2')
        self.assertEqual(set(old), set(new))
        self.assertNotEqual(old['tokens'], new['tokens'])
        self.assertNotEqual(old['components'], new['components'])
        self.assertNotEqual(old['componentBindings'], new['componentBindings'])
        self.assertNotEqual(old['fontBindings'], new['fontBindings'])
        for profile in (old, new):
            for key in ('tokens', 'components', 'fidelity'):
                self.assertTrue((ROOT / profile[key]).is_file())
            for platform in ('figma', 'penpot'):
                for key in ('componentBindings', 'fontBindings'):
                    self.assertTrue((ROOT / 'adapters' / platform / 'metadata' / profile[key]).is_file())
        self.assertEqual(load_json(ROOT / new['tokens'])['registryVersion'], '0.2.2')
        self.assertEqual(load_json(ROOT / new['components'])['registryVersion'], '0.2.3')

    def test_old_input_cannot_run_under_new_profile(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'artifacts') as directory:
            output = Path(directory) / 'run'
            command = [sys.executable, 'scripts/run_pipeline.py',
                       'examples/acceptance-prototype', '--output-dir', str(output),
                       '--figma-file', '0vGWSRoLxBiVPXiZ8xJAX9',
                       '--penpot-file', '57949053-620f-8001-8008-c804c8d61529',
                       '--profile', 'v0.2']
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Input versions do not match the selected profile', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
