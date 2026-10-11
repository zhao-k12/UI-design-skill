"""Whole native SVG binding, exact horizontal paints and fractional root clip."""
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import xml.etree.ElementTree as ET
from adapters.headed_table import prepare_source,require
from adapters.headed_table_pixel_regions import source_regions
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash

META=ROOT/'adapters/figma/metadata/headed-table-native'
def evaluate(case):
    source=ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/(case+'-typography')
    plan,texts,lines=source_regions(source)
    path=META/(case+'-svg.json');capture=load_json(path);row=capture['observations'][0]
    require(capture['status']=='PASS' and capture['fileReference']=='0vGWSRoLxBiVPXiZ8xJAX9' and capture['pageReference']=='82:2' and not capture['createdNodeIds'] and not capture['mutatedNodeIds'] and row['logicalId']==plan['logicalId'],'headed_svg_identity_mismatch')
    require(sha256(row['svg'].encode()).hexdigest()==capture['transport']['sha256'] and len(row['svg'])==capture['transport']['length'],'headed_svg_transport_mismatch')
    probe_dir=META/('figma-'+case+'-svg-proof');probe=load_json(probe_dir/'native-svg-raster-report.json');sample=probe['samples'][0]
    require(probe['status']=='PASS' and probe['svgCaptureSha256']==file_hash(path) and probe['referenceComponentIrSha256']==file_hash(source/'component_ir.json') and probe['probeScriptSha256']==file_hash(ROOT/'component-builder/runtime-renderer/native-svg-probe.mjs') and sample['svgSha256']==capture['transport']['sha256'] and sample['pngSha256']==file_hash(probe_dir/sample['pngPath']) and probe['referenceMatches']==[{'logicalId':plan['logicalId'],'screenshotMatches':True,'environmentMatches':True}],'headed_svg_probe_mismatch')
    root=ET.fromstring(row['svg']);ns='{http://www.w3.org/2000/svg}'
    clips=root.findall('.//'+ns+'clipPath')
    require(len(clips)==1 and len(clips[0])==1,'headed_svg_clip_inventory')
    clip=clips[0][0]
    require(clip.tag==ns+'rect' and Decimal(clip.get('width'))==plan['rootBounds']['width'] and Decimal(clip.get('height'))==Decimal(str(plan['rootBounds']['height'])) and clip.get('x','0')==clip.get('y','0')=='0','headed_svg_fractional_clip_mismatch')
    painted=[e for e in root.iter(ns+'rect') if Decimal(e.get('height','0'))==1]
    require(len(painted)==len(lines),'headed_svg_line_inventory')
    for rectangle,line in zip(painted,lines):
        require(rectangle.get('fill','').lower()==line['fill'] and not rectangle.get('transform'),'headed_svg_line_paint_mismatch')
        for key,value in line['region'].items():
            require(Decimal(rectangle.get(key,'0'))==Decimal(str(value)),'headed_svg_line_geometry_mismatch')
    paths=list(root.iter(ns+'path'))
    require(len(paths)==len(texts) and all(p.get('fill','').lower()=='#515a6e' and p.get('fill-rule','nonzero')=='nonzero' for p in paths),'headed_svg_text_path_or_paint_mismatch')
    return {'status':'PASS','captureSha256':file_hash(path),'probe':probe,'horizontalLines':lines,'fractionalRootClip':dict(clip.attrib),'textPathCount':len(paths)},probe_dir/sample['pngPath']
