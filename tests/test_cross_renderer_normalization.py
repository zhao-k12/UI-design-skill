from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest
from adapters.figma.cross_renderer_normalization import run
from validators.ui_ir import ROOT,load_json


class NativeNormalizationTests(unittest.TestCase):
    def test_actual_locked_native_candidates_pass_with_original_native_png(self):
        result=run(ROOT/'artifacts/task-006',ROOT/'adapters/figma/metadata',file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
        self.assertEqual(result['status'],'PASS')
        self.assertEqual([r['checks']['screenshot']['changedPixels'] for r in result['components']],[317,675,311])
        self.assertTrue(all(r['checks']['screenshot']['changedPixelsOutsideEdgeBand']==0 for r in result['components']))

    def test_wrong_content_font_and_offset_cannot_pass_normalization(self):
        for field,value in [('characters','错误'),('fontName',{'family':'Inter','style':'Regular'}),('x',1)]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                metadata=Path(temporary)/'metadata';shutil.copytree(ROOT/'adapters/figma/metadata',metadata)
                directory=metadata/'render-state-captures/action.button.primary.medium'
                evidence=load_json(directory/'native-evidence.json')
                text=next(n for n in evidence['nodes'] if n['type']=='TEXT')
                if field=='x':text['absoluteBounds']['x']+=value
                else:text['properties'][field]=value
                data=json.dumps(evidence,ensure_ascii=False).encode();(directory/'native-evidence.json').write_bytes(data)
                manifest=load_json(directory/'capture_manifest.json');changed=hashlib.sha256(data).hexdigest()
                manifest['nativeEvidenceSha256']=changed;manifest['files']['native-evidence.json']=changed
                (directory/'capture_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
                with self.assertRaises(ValueError):run(ROOT/'artifacts/task-006',metadata,file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
