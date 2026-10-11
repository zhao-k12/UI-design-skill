from copy import deepcopy
import base64
from io import BytesIO
import unittest
from PIL import Image
from adapters.headed_component_library import load
from adapters.component_library_versions import load as load_old
from adapters.headed_table_fidelity import paints,SOURCE,FG,PP
from adapters.headed_table import prepare_source
from adapters.headed_table_raster import check_raster
from adapters.figma.headed_table_vector_proof import evaluate as vector
from adapters.figma.headed_table_instance_qa import validate as fg_instance
from adapters.penpot.headed_table_instance_qa import validate as pp_instance
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import digest

class HeadedTableReleaseTests(unittest.TestCase):
    def test_explicit_new_release_and_unchanged_old_loader(self):
        registry,bindings=load('0.3.0')
        ids=[k for k in registry.snapshot['components'] if k.startswith('data.table.headed.')]
        self.assertEqual(len(ids),2)
        for key in ids:
            self.assertEqual(registry.resolve(key)['descriptor']['slots'],[])
            for platform in bindings:self.assertEqual(bindings[platform].resolve(key)['kind'],'component')
        self.assertEqual(load_old('0.2.1')[0].library_version,'0.2.1')
        with self.assertRaises(ValueError):load('latest')

    def test_versioned_registry_rejects_incomplete_or_expanded_gate(self):
        registry,_=load('0.3.0');catalog=registry.snapshot
        key=next(k for k in catalog['components'] if k.startswith('data.table.headed.'))
        report_id=catalog['components'][key]['fidelity']['reportId']
        reports=load_json(ROOT/'releases/component-library-0.3.0/fidelity-reports.json')
        for kind in ('decision','coverage','alpha','retention','old_policy','missing_platform','failed_platform'):
            changed=deepcopy(reports);r=changed[report_id]
            if kind=='decision':r['decisionSha256']='0'*64
            if kind=='coverage':r['checks']['horizontalCoverage'][0]['rows'][0]['coveredPixels']-=1
            if kind=='alpha':r['checks']['pngContext']['lastRowAlpha']=254
            if kind=='retention':r['checks']['glyphRetention']=[]
            if kind=='old_policy':r['gateVersion']='0.2.1'
            if kind=='missing_platform':r.pop('dualPlatformReports')
            if kind=='failed_platform':r['dualPlatformReports']['figma']['status']='FAIL'
            snapshot=deepcopy(catalog);snapshot['components'][key]['fidelity']['reportSha256']=digest(r)
            with self.assertRaises(ValueError):type(registry)(snapshot,changed)

    def test_actual_four_linked_instances(self):
        for number,case in ((2,'two-column'),(3,'four-column')):
            self.assertEqual(fg_instance(load_json(FG/(case+'-instance.json')),case)['status'],'PASS')
            self.assertEqual(pp_instance(load_json(PP/'instances'/f'discovery-{number}.json'),case)['status'],'PASS')

    def test_missing_line_and_wrong_line_color_rejected(self):
        case='two-column';source=SOURCE/(case+'-typography');plan=prepare_source(source)
        _,vector_png=vector(case);samples=paints(plan,case)
        for kind in ('missing','red','blank_text'):
            image=Image.open(FG/(case+'-native.png')).convert('RGBA')
            if kind=='red':image.putpixel((0,38),(255,0,0,255))
            elif kind=='missing':
                for y in (37,38):
                    for x in range(image.width):image.putpixel((x,y),(248,248,249,255))
            else:
                b=samples[0]['region']
                for y in range(int(b['y']),int(b['y']+b['height'])+1):
                    for x in range(int(b['x']),int(b['x']+b['width'])+1):image.putpixel((x,y),(248,248,249,255))
            output=BytesIO();image.save(output,format='PNG')
            with self.assertRaises(ValueError):check_raster(source,'figma',output.getvalue(),vector_png,samples)
