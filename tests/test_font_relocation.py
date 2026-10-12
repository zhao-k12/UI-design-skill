from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from scripts.relocate_font_identity import relocate
from scripts.doctor import font_reference


class FontRelocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.font = self.root / 'relocated-font'
        self.font.write_bytes(b'same-font-bytes')
        digest = sha256(self.font.read_bytes()).hexdigest()
        self.identity = {'scope': 'source_font_file_metadata', 'status': 'PASS',
                         'requirements': [{'familyName': 'PingFang SC', 'matches': [{
                             'path': 'old-path', 'fileSha256': digest}]}],
                         'files': [{'path': 'old-path', 'sha256': digest}], 'admissionEligible': False}

    def test_equal_font_bytes_relocate_paths_without_modifying_original_or_admission(self):
        original = deepcopy(self.identity)
        updated = relocate(self.identity, self.font, 'PingFang SC')
        self.assertEqual(self.identity, original)
        self.assertEqual(updated['requirements'][0]['matches'][0]['path'], str(self.font.resolve()))
        self.assertEqual(updated['files'][0]['path'], str(self.font.resolve()))
        self.assertFalse(updated['admissionEligible'])

    def test_different_font_bytes_are_never_substituted(self):
        self.font.write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'substitution'):
            relocate(self.identity, self.font, 'PingFang SC')

    def test_ambiguous_or_unapproved_metadata_cannot_be_relocated(self):
        with self.assertRaises(ValueError):
            relocate(self.identity, self.font, 'Unknown')
        self.identity['status'] = 'REVIEW'
        with self.assertRaises(ValueError):
            relocate(self.identity, self.font, 'PingFang SC')

    def test_font_preflight_reports_missing_changed_and_exact_file(self):
        target = self.root / 'identity.json'
        target.write_text(json.dumps(relocate(self.identity, self.font, 'PingFang SC')), encoding='utf-8')
        self.assertEqual(font_reference(self.root, target)['status'], 'PASS')
        self.font.write_bytes(b'changed')
        self.assertEqual(font_reference(self.root, target)['status'], 'FAIL')
        self.font.unlink()
        self.assertEqual(font_reference(self.root, target)['status'], 'MISSING')
