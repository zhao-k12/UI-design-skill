import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from adapters.figma.table_fidelity import run
from validators.ui_ir import ROOT,load_json


class TableFidelityTests(unittest.TestCase):
    def test_actual_native_table_passes_with_exact_nontext_geometry(self):
        result=run(ROOT/'adapters/figma/metadata',file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
        report=result['report'];self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['checks']['screenshot']['changedPixels'],2415)
        self.assertEqual(result['proof']['nontextChangedPixels'],0)
        self.assertEqual(len(result['proof']['baselines']),9)

    def test_wrong_font_and_border_cannot_be_hidden_by_valid_capture_hashes(self):
        for changed in ('font','border'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as temporary:
                metadata=Path(temporary)/'metadata';shutil.copytree(ROOT/'adapters/figma/metadata',metadata)
                directory=metadata/'table-native-capture-v2';evidence=load_json(directory/'native-evidence.json')
                if changed=='font':next(n for n in evidence['nodes'] if n['type']=='TEXT')['properties']['fontWeight']=600
                else:next(n for n in evidence['nodes'] if n['name'].startswith('source/row-border/'))['properties']['fills'][0]['color']['r']=0
                data=json.dumps(evidence,ensure_ascii=False).encode();(directory/'native-evidence.json').write_bytes(data)
                manifest=load_json(directory/'capture_manifest.json');sha=hashlib.sha256(data).hexdigest();manifest['nativeEvidenceSha256']=sha;manifest['files']['native-evidence.json']=sha
                (directory/'capture_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
                with self.assertRaises(ValueError):run(metadata,file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
