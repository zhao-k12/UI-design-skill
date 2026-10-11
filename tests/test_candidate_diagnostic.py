"""Independent diagnostic fixtures stay test-fixture and never qualify for admission."""
from copy import deepcopy
import hashlib
from io import BytesIO
from pathlib import Path
import struct
import tempfile
import unittest

from PIL import Image
from adapters.figma.native_capture import save_capture
from adapters.figma.candidate_diagnostic import compare_candidate
import test_button_candidate as button_fixtures
import test_form_candidate as form_fixtures
from validators.ui_ir import ROOT


class CandidateDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='diagnostic-tests-',dir=ROOT/'artifacts')
        self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name)
        source=button_fixtures.ButtonCandidateTests();source.setUp();self.reference=source.component
        self.reference['environment']={'deviceScaleFactor':1}
        self.reference['nodes'][0]['bounds']={'x':0,'y':0,'width':60,'height':32}
        self.reference['nodes'][1]['bounds']={'x':16,'y':5.5,'width':28,'height':21}
        stream=BytesIO();Image.new('RGBA',(60,32),(45,140,240,255)).save(stream,format='PNG')
        self.png=stream.getvalue();self.reference_png=self.directory/'reference.png';self.reference_png.write_bytes(self.png)
        self.reference['screenshot']={'sha256':hashlib.sha256(self.png).hexdigest()}
        blue={'type':'SOLID','color':{'r':45/255,'g':140/255,'b':240/255}}
        white={'type':'SOLID','color':{'r':1,'g':1,'b':1}}
        root={'reference':'root','parentReference':None,'type':'COMPONENT','name':'candidate/fixture.button',
            'localBounds':{'x':80,'y':80,'width':60,'height':32},'absoluteBounds':{'x':80,'y':80,'width':60,'height':32},
            'properties':{'fills':[deepcopy(blue)],'strokes':[deepcopy(blue)],'strokeWeight':1,'strokeAlign':'INSIDE',
                'cornerRadius':4,'paddingTop':0,'paddingRight':15,'paddingBottom':0,'paddingLeft':15}}
        label={'reference':'label','parentReference':'root','type':'TEXT','name':'查询',
            'localBounds':{'x':16,'y':5.5,'width':28,'height':21},'absoluteBounds':{'x':96,'y':85.5,'width':28,'height':21},
            'properties':{'characters':'查询','fontName':{'family':'FixtureSource','style':'Regular'},
                'fontSize':14,'fontWeight':400,'lineHeight':{'unit':'PIXELS','value':21},'fills':[white]}}
        self.result={'scope':'figma_native_component_capture','status':'PASS','evidenceKind':'native-platform-export',
            'evidenceScope':'test-fixture','captureId':'fixture-capture','exporterVersion':'fixture',
            'fileReference':'fixture','componentReference':'root','logicalId':'fixture.button',
            'admissionEligible':False,'fidelityGate':'NOT_RUN','createdNodeIds':[],'mutatedNodeIds':[],'issues':[],
            'nativeEvidence':{'rootReference':'root','pageReference':'page','nodes':[root,label]},
            'raster':{'format':'PNG','scale':1,'background':'native-transparent','bytes':list(self.png)}}
        self.fonts={'observations':[{'logicalId':'fixture.button','path':'0.0','surface':'element',
            'fonts':[{'familyName':'FixtureSource','glyphCount':2}]}]}

    def compare(self,result=None,**kwargs):
        target=self.directory/('capture-'+str(len(list(self.directory.iterdir()))))
        save_capture(result or self.result,target,file_reference='fixture',component_reference='root',logical_id='fixture.button',scope='test-fixture')
        return compare_candidate(self.reference,self.fonts,target,self.reference_png,file_reference='fixture',scope='test-fixture',**kwargs)

    def test_exact_known_properties_and_pixels_still_require_complete_fidelity(self):
        report=self.compare(bindings={'FixtureSource':{'family':'FixtureSource','style':'Regular'}})
        self.assertTrue(all(item['status']=='PASS' for item in report['checks']))
        self.assertEqual(report['raster']['changedPixels'],0)
        self.assertEqual(report['status'],'REVIEW');self.assertFalse(report['admissionEligible'])

    def test_measured_baseline_span_preserves_source_layout_without_admission(self):
        changed=deepcopy(self.result);label=changed['nativeEvidence']['nodes'][1]
        span={'reference':'span','parentReference':'root','type':'FRAME','name':'source/0.0',
            'localBounds':{'x':16,'y':5.5,'width':28,'height':21},'absoluteBounds':{'x':96,'y':85.5,'width':28,'height':21},
            'properties':{'fills':[],'strokes':[],'clipsContent':False}}
        label['parentReference']='span';label['localBounds'].update(x=0,y=-1)
        label['absoluteBounds']['y']=84.5
        changed['nativeEvidence']['nodes'].insert(1,span)
        report=self.compare(changed)
        self.assertEqual(report['status'],'REVIEW')
        self.assertTrue(all(item['status']=='PASS' for item in report['checks']))
        self.assertTrue(any('baseline alignment' in item for item in report['unverified']))
        self.assertEqual(report['fidelityGate'],'NOT_RUN')

    def test_border_color_typography_and_native_geometry_drift_are_identified(self):
        for role,key,value,field in [(0,'strokeWeight',2,'button.strokeWeight'),(0,'cornerRadius',8,'button.radius'),
                (1,'fontSize',15,'label.fontSize'),(1,'characters','other','label.characters')]:
            changed=deepcopy(self.result);changed['nativeEvidence']['nodes'][role]['properties'][key]=value
            report=self.compare(changed)
            self.assertIn(field,{item['field'] for item in report['checks'] if item['status']=='FAIL'})
            self.assertEqual(report['status'],'FAIL')
        changed=deepcopy(self.result);changed['nativeEvidence']['nodes'][1]['absoluteBounds']['x']=97
        self.assertEqual(self.compare(changed)['status'],'FAIL')

    def test_float32_storage_is_checked_exactly_without_visual_tolerance(self):
        changed=deepcopy(self.result)
        paint=changed['nativeEvidence']['nodes'][0]['properties']['fills'][0]['color']
        paint['r']=struct.unpack('f',struct.pack('f',45/255))[0]
        self.assertEqual(self.compare(changed)['status'],'REVIEW')
        paint['r']+=0.000001
        report=self.compare(changed)
        self.assertIn('button.fill',{item['field'] for item in report['checks'] if item['status']=='FAIL'})

    def test_pixel_drift_is_not_hidden_as_antialiasing(self):
        changed=deepcopy(self.result);image=Image.new('RGBA',(60,32),(45,140,240,255));image.putpixel((0,0),(44,140,240,255))
        stream=BytesIO();image.save(stream,format='PNG');changed['raster']['bytes']=list(stream.getvalue())
        report=self.compare(changed)
        self.assertEqual(report['raster']['changedPixels'],1);self.assertEqual(report['status'],'FAIL')

    def test_scope_wrong_identity_missing_capture_and_mixed_values(self):
        directory=self.directory/'fixture-scope'
        save_capture(self.result,directory,file_reference='fixture',component_reference='root',logical_id='fixture.button',scope='test-fixture')
        production=compare_candidate(self.reference,self.fonts,directory,self.reference_png,file_reference='fixture')
        self.assertEqual(production['status'],'FAIL')
        missing=compare_candidate(self.reference,self.fonts,None,self.reference_png,file_reference='fixture')
        self.assertEqual(missing['status'],'REVIEW');self.assertEqual(missing['issues'][0]['code'],'missing_native_candidate')
        changed=deepcopy(self.result);changed['nativeEvidence']['nodes'][1]['properties']['fontSize']={'nativeMixed':True}
        self.assertIn('REVIEW',{item['status'] for item in self.compare(changed)['checks']})

    def test_saved_capture_tamper_is_rejected_before_comparison(self):
        directory=self.directory/'tamper'
        save_capture(self.result,directory,file_reference='fixture',component_reference='root',logical_id='fixture.button',scope='test-fixture')
        (directory/'native.png').write_bytes(b'changed')
        report=compare_candidate(self.reference,self.fonts,directory,self.reference_png,file_reference='fixture',scope='test-fixture')
        self.assertEqual(report['status'],'FAIL');self.assertEqual(report['checks'],[])

    def form_case(self,kind):
        source,_=form_fixtures.fixture(kind)
        source['environment']={'deviceScaleFactor':1}
        stream=BytesIO();Image.new('RGBA',(240,32),'white').save(stream,format='PNG')
        raw=stream.getvalue();reference_png=self.directory/(kind+'.png');reference_png.write_bytes(raw)
        source['screenshot']={'sha256':hashlib.sha256(raw).hexdigest()}
        nodes=[]
        def layer(reference,parent,name,node_type,bounds,props):
            absolute=dict(bounds,x=bounds['x']+80,y=bounds['y']+80)
            nodes.append({'reference':reference,'parentReference':parent,'name':name,'type':node_type,
                'localBounds':dict(bounds),'absoluteBounds':absolute,'properties':props})
        bluegray={'type':'SOLID','color':{'r':220/255,'g':222/255,'b':226/255}}
        white={'type':'SOLID','color':{'r':1,'g':1,'b':1}}
        layer('root',None,'candidate/'+source['logicalComponentId'],'COMPONENT',{'x':0,'y':0,'width':240,'height':32},{'fills':[],'strokes':[]})
        padding={'paddingTop':4,'paddingRight':7,'paddingBottom':4,'paddingLeft':7} if kind=='Input' else {key:0 for key in ('paddingTop','paddingRight','paddingBottom','paddingLeft')}
        layer('field','root','source/0.1' if kind=='Input' else 'source/0.0','FRAME',{'x':0,'y':0,'width':240,'height':32},
            {'fills':[white],'strokes':[bluegray],'strokeWeight':1,'strokeAlign':'INSIDE','cornerRadius':4,**padding})
        def label_props(value,family,color,line):
            return {'characters':value,'fontName':{'family':family,'style':'Regular'},'fontSize':14,'fontWeight':400,
                'lineHeight':line,'fills':[{'type':'SOLID','color':dict(zip(('r','g','b'),(n/255 for n in color)))}]}
        observations=[]
        if kind=='Input':
            layer('label','field','source/placeholder','TEXT',{'x':8,'y':5,'width':70,'height':22},
                label_props('请输入姓名','FixtureText',(197,200,206),{'unit':'AUTO'}))
            observations.append({'logicalId':source['logicalComponentId'],'path':'0.1','surface':'element','fonts':[{'familyName':'FixtureText','glyphCount':5}]})
        else:
            box={'x':1,'y':1,'width':238,'height':30}
            layer('content','field','source/0.0.1','FRAME',box,{})
            layer('slot','content','source/selected-value','FRAME',box,{})
            layer('label','slot','source/selected-value-text','TEXT',{'x':9,'y':1,'width':28,'height':30},
                label_props('启用','FixtureText',(81,90,110),{'unit':'PIXELS','value':30}))
            layer('arrow','content','source/ionicons-arrow','TEXT',{'x':217,'y':9,'width':14,'height':14},
                {**label_props('\uf116','FixtureIcons',(81,90,110),{'unit':'PIXELS','value':14}),'layoutPositioning':'ABSOLUTE'})
            observations=[{'logicalId':source['logicalComponentId'],'path':path,'surface':surface,'fonts':[{'familyName':family,'glyphCount':1}]} for path,surface,family in [('0.0.1.0','element','FixtureText'),('0.0.1.1','pseudo:before','FixtureIcons')]]
        result=deepcopy(self.result);result.update(logicalId=source['logicalComponentId'],
            nativeEvidence={'rootReference':'root','pageReference':'page','nodes':nodes},raster={'format':'PNG','scale':1,'background':'native-transparent','bytes':list(raw)})
        return source,{'observations':observations},result,reference_png

    def test_input_normal_line_height_stays_unverified_and_placeholder_color_is_checked(self):
        source,fonts,result,png=self.form_case('Input');directory=self.directory/'input'
        save_capture(result,directory,file_reference='fixture',component_reference='root',logical_id=source['logicalComponentId'],scope='test-fixture')
        report=compare_candidate(source,fonts,directory,png,file_reference='fixture',scope='test-fixture')
        self.assertEqual(report['status'],'REVIEW')
        self.assertTrue(all(item['status']=='PASS' for item in report['checks']))
        self.assertTrue(any('normal line-height' in item for item in report['unverified']))

    def test_select_arrow_geometry_glyph_and_font_roles_are_checked(self):
        source,fonts,result,png=self.form_case('Select');directory=self.directory/'select'
        save_capture(result,directory,file_reference='fixture',component_reference='root',logical_id=source['logicalComponentId'],scope='test-fixture')
        report=compare_candidate(source,fonts,directory,png,file_reference='fixture',scope='test-fixture')
        self.assertEqual(report['status'],'REVIEW');self.assertTrue(all(item['status']=='PASS' for item in report['checks']))
        result['nativeEvidence']['nodes'][-1]['properties']['characters']='v';other=self.directory/'select-drift'
        save_capture(result,other,file_reference='fixture',component_reference='root',logical_id=source['logicalComponentId'],scope='test-fixture')
        report=compare_candidate(source,fonts,other,png,file_reference='fixture',scope='test-fixture')
        self.assertIn('arrow.characters',{item['field'] for item in report['checks'] if item['status']=='FAIL'})
