"""Diagnostic boundaries: complete issue lists, byte integrity and strict group routing."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.doctor import evidence_check, runtime_reference, status_of
from scripts.run_checks import command_for, main


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def manifest(self, files, status='PASS'):
        (self.root / 'manifest.json').write_text(json.dumps({'status': status, 'files': files}), encoding='utf-8')
        return evidence_check(self.root, 'manifest.json')

    def test_lists_missing_changed_and_escaped_evidence_together(self):
        target = self.root / 'changed.txt'
        target.write_bytes(b'changed')
        report = self.manifest({'missing-a': '0' * 64, 'missing-b': '0' * 64,
                                'changed.txt': '0' * 64, '../outside': '0' * 64,
                                'C:/outside': '0' * 64})
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(len(report['issues']), 5)
        self.assertEqual([i['status'] for i in report['issues']].count('MISSING'), 2)
        self.assertEqual(target.read_bytes(), b'changed')

    def test_exact_manifest_bytes_pass_but_never_imply_native_acceptance(self):
        (self.root / 'proof').write_bytes(b'raw\r\nbytes')
        report = self.manifest({'proof': sha256(b'raw\r\nbytes').hexdigest()})
        self.assertEqual(report['status'], 'PASS')
        self.assertIn('NOT_RUN', report['detail'])
        (self.root / 'proof').write_bytes(b'raw\nbytes')
        self.assertEqual(evidence_check(self.root, 'manifest.json')['status'], 'FAIL')

    def test_invalid_manifest_cannot_claim_pass(self):
        for files, status in [({}, 'PASS'), ({'file': 'bad-hash'}, 'PASS'), ({'file': '0' * 64}, 'FAIL')]:
            self.assertEqual(self.manifest(files, status)['status'], 'FAIL')
        (self.root / 'manifest.json').write_text('[]', encoding='utf-8')
        self.assertEqual(evidence_check(self.root, 'manifest.json')['status'], 'FAIL')

    def reference(self):
        base = self.root / 'artifacts/task-006'
        base.mkdir(parents=True)
        lock_path = self.root / 'component-builder/source-reader/source-lock.json'
        lock_path.parent.mkdir(parents=True)
        lock_path.write_text('{"sourceVersion":"locked"}', encoding='utf-8')
        renderer = self.root / 'component-builder/runtime-renderer/extract.mjs'
        renderer.parent.mkdir(parents=True)
        renderer.write_bytes(b'original-renderer')
        (base / 'official-runtime-gallery.png').write_bytes(b'gallery')
        components = []
        for kind in ('Button', 'Input', 'Select'):
            (base / (kind + '.png')).write_bytes(kind.encode())
            components.append({'componentType': kind, 'screenshot': {
                'path': kind + '.png', 'sha256': sha256(kind.encode()).hexdigest()}})
        (base / 'component_ir.json').write_text(json.dumps({'status': 'PASS', 'components': components}), encoding='utf-8')
        (base / 'runtime_manifest.json').write_text(json.dumps({'provenance': {
            'sourceLockSha256': sha256(lock_path.read_bytes()).hexdigest(),
            'rendererSha256': sha256(renderer.read_bytes()).hexdigest()},
            'gallerySha256': sha256(b'gallery').hexdigest()}), encoding='utf-8')
        (base / 'extraction_report.json').write_text(json.dumps({'status': 'PASS', 'sourceVersion': 'locked',
            'componentIrSha256': sha256((base / 'component_ir.json').read_bytes()).hexdigest(),
            'runtimeManifestSha256': sha256((base / 'runtime_manifest.json').read_bytes()).hexdigest()}), encoding='utf-8')
        return base, renderer

    def test_reference_rejects_changed_renderer_and_raw_screenshots(self):
        base, renderer = self.reference()
        self.assertEqual(runtime_reference(self.root)['status'], 'PASS')
        renderer.write_bytes(b'changed-renderer')
        self.assertEqual(runtime_reference(self.root)['status'], 'FAIL')
        renderer.write_bytes(b'original-renderer')
        (base / 'Button.png').write_bytes(b'changed')
        self.assertEqual(runtime_reference(self.root)['status'], 'FAIL')

    def test_missing_reference_screenshot_is_missing_not_pass(self):
        base, _ = self.reference()
        (base / 'Select.png').unlink()
        self.assertEqual(runtime_reference(self.root)['status'], 'MISSING')

    def test_missing_browser_reference_reports_all_initial_files(self):
        report = runtime_reference(self.root)
        self.assertEqual(report['status'], 'MISSING')
        self.assertEqual(len(report['missing']), 3)

    def test_partial_reference_is_not_pass(self):
        base = self.root / 'artifacts/task-006'
        base.mkdir(parents=True)
        for name in ('component_ir.json', 'runtime_manifest.json', 'extraction_report.json'):
            (base / name).write_text('{"status":"RUNNING"}', encoding='utf-8')
        self.assertEqual(runtime_reference(self.root)['status'], 'FAIL')

    def test_runtime_groups_use_explicit_files_and_native_is_never_a_mock_test(self):
        (self.root / 'tests').mkdir()
        for name in ('b.test.mjs', 'a.test.mjs'):
            (self.root / 'tests' / name).touch()
        command = command_for('runtime', self.root, node='node-path')
        self.assertEqual(command[:2], ['node-path', '--test'])
        self.assertTrue(command[2].endswith('a.test.mjs'))
        with self.assertRaises(ValueError):
            command_for('native')

    def test_missing_prerequisites_invalidate_old_success_without_starting_tests(self):
        output = self.root / 'artifacts/checks'
        output.mkdir(parents=True)
        (output / 'checks.json').write_text('{"status":"PASS"}', encoding='utf-8')
        packet = {'status': 'MISSING', 'checks': []}
        with patch('scripts.run_checks.ROOT', self.root), patch('scripts.run_checks.diagnose', return_value=packet), \
                patch('scripts.run_checks.subprocess.run') as run, \
                patch('sys.argv', ['run_checks.py', '--group', 'runtime', '--output-dir', str(output)]):
            self.assertEqual(main(), 1)
            run.assert_not_called()
        report = json.loads((output / 'checks.json').read_text())
        self.assertEqual(report['status'], 'MISSING')
        self.assertEqual(report['tests'], 'NOT_RUN')
        self.assertFalse(report['releaseReady'])

    def test_not_run_is_never_pass(self):
        self.assertEqual(status_of([{'status': 'PASS'}, {'status': 'NOT_RUN'}]), 'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
