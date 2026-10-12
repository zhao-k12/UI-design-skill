from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.evidence_package import build, load_json, verify, NATIVE_ROLES, VERSION_KEYS


class EvidencePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.artifacts = self.root / 'artifacts'
        self.output = self.artifacts / 'bundle'
        (self.source / 'proof.json').write_bytes(b'{"scope":"test-fixture","status":"NOT_RUN"}\r\n')
        self.plan = {'scope': 'portable-evidence-package', 'contractVersion': '0.1.0',
                     'packageId': 'test-package', 'releaseVersion': 'test-only', 'purpose': 'development',
                     'versions': {'test': '1'}, 'coverage': [], 'evidenceSets': [],
                     'artifacts': [{'id': 'proof', 'source': 'proof.json', 'path': 'evidence/proof.json',
                                    'role': 'diagnostic', 'distribution': {
                                        'status': 'redistributable', 'basis': 'Synthetic test fixture'}}]}

    def pack(self):
        plan_path = self.source / 'plan.json'
        plan_path.write_text(json.dumps(self.plan), encoding='utf-8')
        return build(plan_path, self.source, self.output, artifact_root=self.artifacts)

    def mutate(self, callback):
        path = self.output / 'manifest.json'
        manifest = load_json(path)
        callback(manifest)
        path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_bundle_is_self_contained_after_source_removed_and_bundle_moved(self):
        self.assertEqual(self.pack()['status'], 'PASS')
        shutil.rmtree(self.source)
        moved = self.root / 'moved'
        shutil.copytree(self.output, moved)
        packet = verify(moved)
        self.assertEqual(packet['status'], 'PASS')
        self.assertEqual((moved / 'evidence/proof.json').read_bytes(), b'{"scope":"test-fixture","status":"NOT_RUN"}\r\n')
        self.assertFalse(packet['releaseReady'])
        self.assertEqual(packet['nativeAcceptance'], 'NOT_RUN')

    def test_changed_and_missing_files_are_both_reported(self):
        extra = deepcopy(self.plan['artifacts'][0])
        extra.update(id='extra', path='evidence/extra.json')
        self.plan['artifacts'].append(extra)
        self.assertEqual(self.pack()['status'], 'PASS')
        (self.output / 'evidence/proof.json').write_bytes(b'changed')
        (self.output / 'evidence/extra.json').unlink()
        codes = {i['code'] for i in verify(self.output)['issues']}
        self.assertEqual(codes, {'artifact_changed', 'missing_artifact'})

    def test_unlisted_payload_is_rejected(self):
        self.pack()
        (self.output / 'unlisted.txt').write_bytes(b'not-declared')
        self.assertIn('unlisted_artifact', {i['code'] for i in verify(self.output)['issues']})

    def test_nonportable_paths_never_create_a_bundle(self):
        for path in ('../escape', 'C:/escape', '/absolute', 'evidence\\proof.json',
                     'evidence/CON.txt', 'evidence/item.', 'evidence//item', 'manifest.json', 'manifest.json/child'):
            self.plan['artifacts'][0]['path'] = path
            self.assertEqual(self.pack()['status'], 'FAIL', path)
            self.assertFalse(self.output.exists())

    def test_case_collision_and_file_directory_overlap_are_rejected(self):
        extra = deepcopy(self.plan['artifacts'][0])
        extra.update(id='extra', path='Evidence/PROOF.json')
        self.plan['artifacts'].append(extra)
        self.assertEqual(self.pack()['status'], 'FAIL')
        extra['path'] = 'evidence/proof.json/child'
        self.assertEqual(self.pack()['status'], 'FAIL')

    def test_missing_sources_aggregate_without_partial_output(self):
        self.plan['artifacts'][0]['source'] = 'missing-one'
        extra = deepcopy(self.plan['artifacts'][0])
        extra.update(id='extra', source='missing-two', path='evidence/extra.json')
        self.plan['artifacts'].append(extra)
        packet = self.pack()
        self.assertEqual(packet['status'], 'MISSING')
        self.assertEqual(len(packet['issues']), 2)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_never_replaced(self):
        self.pack()
        before = (self.output / 'manifest.json').read_bytes()
        self.assertEqual(self.pack()['status'], 'FAIL')
        self.assertEqual((self.output / 'manifest.json').read_bytes(), before)

    def test_plan_must_explicitly_declare_distribution(self):
        self.plan['artifacts'][0]['distribution']['status'] = 'unknown'
        self.assertEqual(self.pack()['status'], 'FAIL')
        self.assertFalse(self.output.exists())

    def test_native_missing_roles_versions_and_platform_sets_are_aggregated(self):
        self.plan['purpose'] = 'native-acceptance'
        self.plan['coverage'] = [{'id': 'sample', 'logicalId': 'action.button',
                                  'configurationId': 'default', 'platforms': ['figma', 'penpot']}]
        self.plan['evidenceSets'] = [{'coverageId': 'sample', 'platform': 'figma',
                                      'artifacts': {'diagnostic': 'proof'}}]
        packet = self.pack()
        self.assertEqual(packet['status'], 'MISSING')
        codes = [i['code'] for i in packet['issues']]
        self.assertEqual(codes.count('missing_evidence_role'), len(NATIVE_ROLES))
        self.assertEqual(codes.count('missing_version_lock'), len(VERSION_KEYS))
        self.assertEqual(codes.count('missing_evidence_set'), 1)

    def test_reference_roles_must_match_artifact_and_coverage(self):
        self.plan['evidenceSets'] = [{'coverageId': 'unknown', 'platform': 'figma',
                                      'artifacts': {'native-png': 'proof', 'source': 'absent'}}]
        packet = self.pack()
        self.assertEqual(packet['status'], 'FAIL')
        self.assertEqual(sum(i['code'] == 'invalid_evidence_reference' for i in packet['issues']), 2)

    def test_duplicate_json_and_extra_schema_fields_cannot_claim_success(self):
        self.pack()
        path = self.output / 'manifest.json'
        path.write_text('{"scope":1,"scope":2}', encoding='utf-8')
        self.assertEqual(verify(self.output)['status'], 'FAIL')
        self.assertFalse(verify(self.output)['releaseReady'])

    def test_manifest_cannot_reference_external_sources_after_packaging(self):
        self.pack()
        self.mutate(lambda m: m['artifacts'][0].update(source='external-file'))
        self.assertIn('schema_invalid', {i['code'] for i in verify(self.output)['issues']})

    def test_bundle_missing_manifest_is_missing(self):
        self.assertEqual(verify(self.root / 'absent')['status'], 'MISSING')

    def test_source_traversal_is_rejected_before_read(self):
        self.plan['artifacts'][0]['source'] = '../outside'
        self.assertEqual(self.pack()['status'], 'FAIL')
        self.assertFalse(self.output.exists())

    def test_all_native_role_labels_still_do_not_prove_native_acceptance(self):
        self.plan['purpose'] = 'native-acceptance'
        self.plan['versions'] = {key: 'test-only' for key in VERSION_KEYS}
        self.plan['coverage'] = [{'id': 'sample', 'logicalId': 'action.button',
                                  'configurationId': 'test-only', 'platforms': ['figma']}]
        template = self.plan['artifacts'][0]
        self.plan['artifacts'] = []
        refs = {}
        for role in sorted(NATIVE_ROLES):
            entry = deepcopy(template)
            entry.update(id='artifact-' + role, path='evidence/' + role + '.json', role=role)
            self.plan['artifacts'].append(entry)
            refs[role] = entry['id']
        self.plan['evidenceSets'] = [{'coverageId': 'sample', 'platform': 'figma', 'artifacts': refs}]
        packet = self.pack()
        self.assertEqual(packet['status'], 'PASS')
        self.assertFalse(packet['releaseReady'])
        self.assertEqual(packet['nativeAcceptance'], 'NOT_RUN')
        self.assertEqual(verify(self.output)['nativeAcceptance'], 'NOT_RUN')
