"""Approved TASK-020 edge ownership, coverage and retained glyph paint checks."""
from io import BytesIO
from math import floor,ceil
from PIL import Image
from adapters.headed_table import require
from adapters.headed_table_pixel_regions import compare_regions,source_regions,intersects
from validators.visual.cross_renderer import edge_band,glyph_retention

def check_raster(source_dir,platform,raw,vector_png,paint_samples):
    from pathlib import Path
    import json
    ownership=compare_regions(source_dir,platform,raw)
    plan,texts,lines=source_regions(source_dir)
    source=json.loads((Path(source_dir)/'component_ir.json').read_text(encoding='utf8'))['components'][0]
    reference=Image.open(Path(source_dir)/source['screenshot']['path']).convert('RGBA')
    actual=Image.open(BytesIO(raw)).convert('RGBA');vector=Image.open(vector_png).convert('RGBA')
    require(actual.size==vector.size,'headed_vector_raster_size_mismatch')
    band=edge_band(vector);outside=0
    for y in range(actual.height):
        for x in range(actual.width):
            if reference.getpixel((x,y))!=actual.getpixel((x,y)) and (x,y) not in band:outside+=1
    require(outside==0,'headed_difference_outside_independent_edge_band')
    coverage=[]
    rgb=lambda value:tuple(int(value[i:i+2],16) for i in (1,3,5))
    for line in lines:
        region=line['region'];rows=[]
        for y in range(max(0,floor(region['y'])),min(actual.height,ceil(region['y']+region['height']))):
            values=[actual.getpixel((x,y)) for x in range(actual.width) if intersects(region,x,y)]
            require(values and len(set(values))==1,'headed_horizontal_coverage_discontinuous')
            color=values[0][:3]
            background=(248,248,249) if y<plan['rows'][0]['bounds']['height'] else (255,255,255)
            paints=[rgb(row['fill']) for row in lines if intersects(row['region'],0,y)]+[background]
            require(color!=background,'headed_horizontal_missing_or_occluded')
            require(all(min(p[i] for p in paints)<=color[i]<=max(p[i] for p in paints) for i in range(3)) and color[0]<=color[1]<=color[2],'headed_horizontal_paint_outside_source_palette')
            rows.append({'y':y,'coveredPixels':len(values),'rgba':list(values[0])})
        coverage.append({'sourcePath':line['sourcePath'],'region':region,'sourceFill':line['fill'],'rows':rows,'status':'PASS'})
    retention=glyph_retention(reference,actual,paint_samples)
    require(len(retention)==sum(len(s['characters']) for s in paint_samples) and all(r['status']=='PASS' for r in retention),'headed_glyph_retention_failed')
    return {'status':'PASS','pixelOwnership':ownership,'changedPixelsOutsideEdgeBand':outside,
            'horizontalCoverage':coverage,'glyphRetention':retention,
            'limitations':['Exact native and independent vector geometry and paint remain mandatory upstream.']}
