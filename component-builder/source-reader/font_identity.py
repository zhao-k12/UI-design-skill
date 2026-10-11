"""Read bounded OpenType name metadata; never installs or redistributes fonts."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def read_font_identity(path):
    path=Path(path).resolve()
    if path.stat().st_size>64*1024*1024: raise ValueError('font_file_exceeds_limit')
    data=path.read_bytes()
    def take(offset,length):
        if offset<0 or length<0 or offset+length>len(data): raise ValueError('font_table_out_of_bounds')
        return data[offset:offset+length]
    def unpack(fmt,offset): return struct.unpack(fmt,take(offset,struct.calcsize(fmt)))
    signature=take(0,4)
    if signature==b'ttcf':
        version,count=unpack('>II',4)
        if version not in (0x10000,0x20000) or not 0<count<=128: raise ValueError('unsupported_font_collection')
        offsets=unpack('>'+('I'*count),12)
    elif signature in (b'OTTO',b'\x00\x01\x00\x00',b'true'):
        offsets=(0,)
    else:
        raise ValueError('unsupported_font_container: SFNT/OTF/TTF/TTC only')
    faces=[]
    for index,offset in enumerate(offsets):
        if take(offset,4) not in (b'OTTO',b'\x00\x01\x00\x00',b'true'): raise ValueError('invalid_font_face_signature')
        count=unpack('>H',offset+4)[0]
        if not 0<count<=256: raise ValueError('font_table_count_exceeds_limit')
        tables={}
        for entry in range(count):
            tag,_,start,length=unpack('>4sIII',offset+12+entry*16)
            if tag in tables: raise ValueError('duplicate_font_table')
            tables[tag]=take(start,length)
        name=tables.get(b'name')
        if name is None or len(name)<6: raise ValueError('font_name_table_missing')
        version,record_count,storage=struct.unpack_from('>HHH',name)
        if version not in (0,1) or record_count>4096 or storage<6+record_count*12 or storage>len(name):
            raise ValueError('invalid_font_name_header')
        languages=[]
        if version==1:
            at=6+record_count*12
            if at+2>len(name): raise ValueError('truncated_font_language_tags')
            language_count=struct.unpack_from('>H',name,at)[0]
            if at+2+language_count*4>storage: raise ValueError('invalid_font_language_tags')
            for language_index in range(language_count):
                length,start=struct.unpack_from('>HH',name,at+2+language_index*4)
                if storage+start+length>len(name): raise ValueError('font_language_tag_out_of_bounds')
                try: languages.append(name[storage+start:storage+start+length].decode('utf-16-be'))
                except UnicodeDecodeError as exc: raise ValueError('invalid_font_language_tag_encoding') from exc
        records=[];unsupported=[]
        for entry in range(record_count):
            at=6+entry*12
            if at+12>len(name): raise ValueError('truncated_font_name_record')
            platform,encoding,language,name_id,length,start=struct.unpack_from('>HHHHHH',name,at)
            if language>=0x8000 and (version!=1 or language-0x8000>=len(languages)):
                raise ValueError('font_name_language_tag_unknown')
            if name_id not in (1,2,5,6,16,17): continue
            if storage+start+length>len(name): raise ValueError('font_name_string_out_of_bounds')
            raw=name[storage+start:storage+start+length]
            codec='utf-16-be' if platform==0 or (platform==3 and encoding in (0,1,10)) else 'mac_roman' if platform==1 and encoding==0 else None
            if codec is None:
                unsupported.append({'platform':platform,'encoding':encoding,'nameId':name_id});continue
            try: value=raw.decode(codec)
            except UnicodeDecodeError as exc: raise ValueError('invalid_font_name_encoding') from exc
            records.append({'platform':platform,'encoding':encoding,'language':language,'nameId':name_id,'value':value})
        families=[record for record in records if record['nameId'] in (16,1)]
        pairs=[]
        for family in families:
            # Preserve platform/language grouping instead of guessing a translated style.
            peers=[record for record in records if (record['platform'],record['encoding'],record['language'])==(family['platform'],family['encoding'],family['language'])]
            preferred=17 if family['nameId']==16 and any(record['nameId']==17 for record in peers) else 2
            styles=[record['value'] for record in peers if record['nameId']==preferred]
            posts=[record['value'] for record in peers if record['nameId']==6]
            for style in styles:
                for post in posts:
                    pair={'family':family['value'],'style':style,'postScriptName':post}
                    if pair not in pairs: pairs.append(pair)
        if not pairs: raise ValueError('font_family_style_pair_unknown')
        faces.append({'faceIndex':index,'nameTableVersion':version,'languageTags':languages,'namePairs':pairs,'nameRecords':records,
            'unsupportedNameEncodings':unsupported,'hasVariableAxes':b'fvar' in tables})
    return {'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
        'container':signature.decode('ascii',errors='replace'),'faces':faces}


def correlate_fonts(evidence, files):
    if not isinstance(evidence,dict) or evidence.get('scope')!='official_runtime_font_diagnostic' or evidence.get('status')!='PASS':
        raise ValueError('invalid_browser_font_evidence')
    metadata=[];seen_paths=set()
    for entry in files:
        if entry['role'] not in ('system-file-candidate','official-release-sibling'): raise ValueError('unknown_font_file_role')
        item=read_font_identity(entry['path'])
        if item['path'] in seen_paths: raise ValueError('duplicate_font_input')
        seen_paths.add(item['path']);item['role']=entry['role'];metadata.append(item)
    requirements=sorted({(font['familyName'],font['postScriptName'],font['isCustomFont'])
        for item in evidence['observations'] for font in item['fonts'] if font['glyphCount']>0})
    rows=[]
    for family,post,custom in requirements:
        matches=[]
        for item in metadata:
            for face in item['faces']:
                pairs=[pair for pair in face['namePairs'] if pair['family']==family and pair['postScriptName']==post]
                if pairs: matches.append({'path':item['path'],'fileSha256':item['sha256'],'role':item['role'],
                    'faceIndex':face['faceIndex'],'namePairs':pairs})
        styles={pair['style'] for match in matches for pair in match['namePairs']}
        rows.append({'familyName':family,'postScriptName':post,'isCustomFont':custom,'matches':matches,
            'status':'METADATA_IDENTIFIED' if len(matches)==1 and len(styles)==1 else 'REVIEW',
            'fontNameForLoadProbe':{'family':family,'style':next(iter(styles))} if len(matches)==1 and len(styles)==1 else None,
            'association':'Name metadata match only; browser-loaded file identity is not established.'})
    return {'scope':'source_font_file_metadata','status':'PASS' if rows and all(row['status']=='METADATA_IDENTIFIED' for row in rows) else 'REVIEW',
        'referenceComponentIrSha256':evidence['referenceComponentIrSha256'],'requirements':rows,'files':metadata,
        'nativeExecution':'NOT_RUN','fidelityGate':'NOT_RUN','admissionEligible':False,
        'limitations':['No font installation, upload, conversion or redistribution.',
            'SFNT metadata matches do not prove browser cache identity; release siblings do not prove WOFF2 equivalence.',
            'These names are load-probe inputs, not approved native font bindings.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--system-font',type=Path,action='append',default=[])
    parser.add_argument('--release-font',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    output=args.output.resolve()
    if not output.is_relative_to(root/'artifacts'): parser.error('Output must stay in project artifacts')
    inputs=[args.evidence,*args.system_font,*args.release_font]
    if output in {path.resolve() for path in inputs}: parser.error('Output cannot overwrite input')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'status':'RUNNING','admissionEligible':False})+'\n',encoding='utf-8')
    try:
        files=[{'path':path,'role':'system-file-candidate'} for path in args.system_font]+[{'path':path,'role':'official-release-sibling'} for path in args.release_font]
        report=correlate_fonts(json.loads(args.evidence.read_text(encoding='utf-8')),files)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report={'scope':'source_font_file_metadata','status':'FAIL','admissionEligible':False,
            'fidelityGate':'NOT_RUN','issues':[{'code':'invalid_font_metadata','detail':str(exc)}]}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'fonts':[{'family':row['familyName'],'probe':row['fontNameForLoadProbe']} for row in report.get('requirements',[])]},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
