"""Synthetic component fixture: runtime geometry, not prototype visual acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'core/pipeline')]
from confirmed_modules import summary_panel, steps_panel, form_section, page_actions, page_shell, light_tag, sidebar
from html_composition import compile_tree


@pytest.mark.parametrize('brand_text',[None,'CRM系统'])
def test_reusable_summary_and_fluid_fields_at_two_viewports(brand_text):
    with tempfile.TemporaryDirectory(dir=ROOT/'artifacts', prefix='module-quality-') as directory:
        folder=Path(directory);source=folder/'source.txt';source.write_text('synthetic geometry fixture')
        sha=hashlib.sha256(source.read_bytes()).hexdigest()
        def text(identifier,value):return dict(id=identifier,kind='text',value=value)
        summary=summary_panel('summary','Fixture title',tag_node=light_tag('tag','State'),metadata=[text('meta','Reference metadata')])
        steps=steps_panel('progress',dict(id='steps',kind='component',component='Steps',props={'current':1},children=[
            dict(id=f'step-{i}',kind='component',component='Step',props={'title':title}) for i,title in enumerate(['First','Current','Last'])]))
        field=dict(id='field',kind='component',component='FormItem',props={'label':'Field label'},children=[
            dict(id='input',kind='component',component='Input',props={'disabled':True,'placeholder':'Complete placeholder'},slots={'append':[text('suffix','kWh')]})])
        form=form_section('form','Section',[field],label_width=104,columns='auto')
        side=sidebar('side',[{'name':'home','label':'Home','icon':'home-4-line'}],active_name='home',
                     brand_node=text('brand-label',brand_text) if brand_text is not None else None)
        root=page_shell('page',sidebar_node=side,sections=[summary,steps,form,page_actions('actions',[{'label':'Submit','primary':True}])],source_ids=['fixture'])
        traits=dict(leading='none',trailing='none',surface='plain',shape='rect',role='developer-fixture')
        observation=dict(sourceSha256=sha,items=[dict(id='fixture',region='fixture',traits=traits,decision='include',treeRef='page',sourceEvidence='Synthetic fixture only')])
        scan=dict(sourceSha256=sha,items=[dict(id='fixture',region='fixture',traits=traits,visual='Synthetic fixture only')])
        content=dict(sourceSha256=sha,title='Geometry fixture',root=root,layoutQualityPolicy='form-and-modules-v1')
        compiled=compile_tree(source,content,observation,scan)
        core=folder/'core';core.mkdir()
        ir=core/'ui_ir.json';ir.write_text(json.dumps(compiled['ui_ir']),encoding='utf-8')
        qa=compiled['qa_report'];qa['uiIrSha256']=hashlib.sha256(ir.read_bytes()).hexdigest()
        (core/'qa_report.json').write_text(json.dumps(qa),encoding='utf-8')
        result=subprocess.run(['node','scripts/export_html_composition.mjs',str(core),str(folder/'html'),'1428','808'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120)
        assert result.returncode==0,result.stdout+result.stderr
        qa=json.loads((folder/'html/qa.json').read_text(encoding='utf-8'))
        assert qa['status']=='PASS'
        assert qa['responsiveQuality']['status']=='PASS'
        timing=qa['machineTiming']
        for phase in ('bundleAndAssetsSeconds','browserLaunchSeconds','layoutPreparationSeconds','staticAndResponsiveSeconds','contactSheetSeconds','browserCloseSeconds','totalSeconds'):
            assert timing[phase]>=0
        assert set(timing['stages'])=={'skeleton','component','delivery'}
        assert timing['totalSeconds']>=sum(stage['totalSeconds'] for stage in timing['stages'].values())
        for stage in timing['stages'].values():
            assert stage['totalSeconds']>=stage['captureAndWriteSeconds']>=0
            assert stage['totalSeconds']>=stage['metricsAndSignaturesSeconds']>=0
        html=(folder/'html/page.html').read_text(encoding='utf-8')
        assert ('data-asset-name="default-logo"' in html)==(brand_text is None)
        if brand_text is not None: assert brand_text in html
        assert (folder/'html/small-viewport.png').is_file()
        for stage in qa['stages'].values():
            checks=stage['layoutQuality']['results']
            close=next(c for c in checks if c['kind']=='summary-close')
            assert close['measurement']==dict(top=16,right=16,width=16,height=16)
            assert next(c for c in checks if c['kind']=='summary-meta-gap')['measurement']['gap']==16
            for check in (c for c in checks if c['kind']=='module-spacing'):
                assert check['measurement']['left']==check['measurement']['right']==24
                assert check['measurement']['gap'] in (None,16)
