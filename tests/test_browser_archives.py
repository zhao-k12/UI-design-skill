import base64
from hashlib import md5
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.install_browser_archives import extract_verified


class BrowserArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive, self.headers = self.root / 'browser.zip', self.root / 'headers.txt'
        self.cache = self.root / 'cache'

    def make(self, member='chrome-win64/chrome.exe'):
        with zipfile.ZipFile(self.archive, 'w') as bundle:
            bundle.writestr(member, b'test-only-executable')
        data = self.archive.read_bytes()
        self.headers.write_text('HTTP/1.1 200 OK\nContent-Length: ' + str(len(data)) +
                                '\nx-goog-hash: md5=' + base64.b64encode(md5(data).digest()).decode() + '\n', encoding='utf-8')

    def install(self):
        return extract_verified(self.archive, self.headers, self.cache, 'chromium-1243', 'chrome-win64')

    def test_exact_archive_installs_without_claiming_dependency_validation(self):
        self.make()
        receipt = self.install()
        self.assertEqual(len(receipt['archiveSha256']), 64)
        self.assertTrue((self.cache / 'chromium-1243/INSTALLATION_COMPLETE').exists())
        self.assertFalse((self.cache / 'chromium-1243/DEPENDENCIES_VALIDATED').exists())
        with self.assertRaisesRegex(ValueError, 'cannot be replaced'):
            self.install()

    def test_changed_download_is_rejected_without_creating_cache(self):
        self.make()
        self.archive.write_bytes(self.archive.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.install()
        self.assertFalse(self.cache.exists())

    def test_zip_traversal_and_wrong_layout_are_rejected(self):
        for member in ('../outside.exe', 'chrome-win64/../outside.exe', 'foreign/browser.exe'):
            self.make(member)
            with self.assertRaises(ValueError):
                self.install()
            self.assertFalse(self.cache.exists())

    def test_missing_executable_does_not_publish_partial_browser(self):
        self.make('chrome-win64/other.exe')
        with self.assertRaisesRegex(ValueError, 'lacks'):
            self.install()
        self.assertFalse((self.cache / 'chromium-1243').exists())
        self.assertEqual(list(self.cache.iterdir()), [])
