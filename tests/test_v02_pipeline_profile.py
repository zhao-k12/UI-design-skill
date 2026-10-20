"""The production CLI routes all design resources by one explicit profile."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
import json
import subprocess
import sys
import tempfile
import unittest

from scripts.run_pipeline import profile_resources
from validators.ui_ir import ROOT, load_json
from adapters.byte_lock import verify as verify_byte_lock, verify_platform, verify_execution_script, script_for_page
from scripts.prepare_adapter_execution import prepare as prepare_execution


class V02PipelineProfileTests(unittest.TestCase):
    def test_profiles_are_complete_and_separate(self):
        old, new = profile_resources('v0.1'), profile_resources('v0.2')
        self.assertEqual(set(old), set(new))
        self.assertNotEqual(old['tokens'], new['tokens'])
        self.assertNotEqual(old['components'], new['components'])
        self.assertNotEqual(old['componentBindings'], new['componentBindings'])
        self.assertNotEqual(old['fontBindings'], new['fontBindings'])
        self.assertNotEqual(old['penpotIconBindings'], new['penpotIconBindings'])
        for profile in (old, new):
            for key in ('tokens', 'components', 'fidelity'):
                self.assertTrue((ROOT / profile[key]).is_file())
            for platform in ('figma', 'penpot'):
                for key in ('componentBindings', 'fontBindings'):
                    self.assertTrue((ROOT / 'adapters' / platform / 'metadata' / profile[key]).is_file())
            self.assertTrue((ROOT / 'adapters/penpot/metadata' / profile['penpotIconBindings']).is_file())
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

    def test_migrated_input_runs_core_and_both_adapter_preflights(self):
        source = ROOT / 'examples/acceptance-prototype-v02'
        manifest = load_json(source / 'input-manifest.json')
        self.assertEqual(manifest['status'], 'READY_FOR_PREFLIGHT')
        with tempfile.TemporaryDirectory(dir=ROOT / 'artifacts') as directory:
            output = Path(directory) / 'run'
            command = [sys.executable, 'scripts/run_pipeline.py', str(source),
                       '--output-dir', str(output),
                       '--figma-file', '0vGWSRoLxBiVPXiZ8xJAX9',
                       '--penpot-file', '57949053-620f-8001-8008-c804c8d61529',
                       '--profile', 'v0.2']
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            qa = load_json(output / 'qa_report.json')
            self.assertEqual(qa['status'], 'PASS')
            self.assertTrue(qa['readyForAdapter'])
            self.assertEqual(qa['adapterPreflights'], {'figma': 'PASS', 'penpot': 'PASS'})
            self.assertEqual(qa['nativeExecution'], 'NOT_RUN')
            self.assertEqual(qa['finalVisualQa'], 'NOT_RUN')
            lock = load_json(output / 'adapter-execution-lock.json')
            plans = {platform: load_json(output / f'{platform}_preflight.json')['plan']
                     for platform in ('figma', 'penpot')}
            self.assertEqual(lock['lockSchemaVersion'], '0.2.0')
            self.assertTrue(verify_byte_lock(lock, plans))
            self.assertEqual(qa['adapterExecutionLockSha256'],
                             sha256((output / 'adapter-execution-lock.json').read_bytes()).hexdigest())
            script = script_for_page('figma', plans['figma'], 0)
            receipt = verify_execution_script(lock, plans, 'figma', script)
            self.assertEqual(receipt['executionScriptSha256'], lock['platforms']['figma']['createScriptSha256'][0])
            intent_dir = Path(directory) / 'figma-execution'
            intent = prepare_execution(output, 'figma', intent_dir)
            self.assertEqual(intent['executionScriptSha256'], sha256((intent_dir / 'execution.js').read_bytes()).hexdigest())
            self.assertEqual(intent['nativeExecution'], 'NOT_RUN')
            self.assertEqual(prepare_execution(output, 'figma', intent_dir), intent)
            with self.assertRaisesRegex(ValueError, 'Execution script differs'):
                verify_execution_script(lock, plans, 'figma', script + '\n')
            (intent_dir / 'execution.js').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'Existing execution artifact differs'):
                prepare_execution(output, 'figma', intent_dir)
            changed = deepcopy(lock)
            changed['platforms']['figma']['sourceFiles']['adapters/figma/runtime.js'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'byte lock changed'):
                verify_byte_lock(changed, plans)
            penpot_changed = deepcopy(lock)
            penpot_changed['platforms']['penpot']['sourceFiles']['adapters/penpot/runtime.js'] = '0' * 64
            self.assertEqual(verify_execution_script(penpot_changed, {'figma': plans['figma']},
                                                     'figma', script)['executionScriptSha256'],
                             receipt['executionScriptSha256'])
            with self.assertRaisesRegex(ValueError, 'byte lock changed for penpot'):
                verify_platform(penpot_changed, 'penpot', plans['penpot'])
            repeated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            (output / 'adapter-execution-lock.json').write_text(
                json.dumps(changed, ensure_ascii=False), encoding='utf-8')
            rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('Adapter byte lock changed', rejected.stdout)


if __name__ == '__main__':
    unittest.main()
