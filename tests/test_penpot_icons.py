"""Official byte source and host scoping; not native platform acceptance."""
from copy import deepcopy
import hashlib
import unittest
from adapters.penpot.icons import prepare_icons
from adapters.penpot.host.server import icon_assets


class IconSourceTests(unittest.TestCase):
    def test_literal_source_bytes_and_write_scope(self):
        payload=prepare_icons('file','page')
        self.assertEqual([i['iconId'] for i in payload['icons']],['remix.settings-3-line','remix.download-line'])
        for icon in payload['icons']:self.assertEqual(hashlib.sha256(icon['svg'].encode()).hexdigest(),icon['svgSha256'])
        served=icon_assets('http://127.0.0.1:60000','file','nonce',payload)
        self.assertIn('buildPenpotIcons(penpot,iconPayload)',served['/plugin.js'][1])
        changed=deepcopy(payload);changed['icons'][0]['svg']=changed['icons'][0]['svg'].replace('17.0002','18.0002',1)
        with self.assertRaises(ValueError):icon_assets('http://127.0.0.1:60000','file','nonce',changed)

    def test_foreign_recovery_record_rejected(self):
        payload=prepare_icons('file','page')
        with self.assertRaises(ValueError):icon_assets('http://127.0.0.1:60000','file','nonce',payload,{'status':'ICONS_CREATED','fileReference':'other'})
