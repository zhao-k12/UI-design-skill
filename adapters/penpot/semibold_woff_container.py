"""Preserve raw OpenType tables when packaging the authorized Semibold as WOFF."""
from io import BytesIO
from pathlib import Path
from hashlib import sha256
import json
from fontTools.ttLib.sfnt import SFNTReader,SFNTWriter

SOURCE=Path('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts/PingFang SC-Semibold.otf')
EXPECTED='ca115f4f17266f1ff5ead3ef1049814eafb4f61cc279134e0a8b3d817532fb78'
raw=SOURCE.read_bytes()
if sha256(raw).hexdigest()!=EXPECTED:raise ValueError('semibold_source_changed')
source=SFNTReader(BytesIO(raw))
stream=BytesIO();writer=SFNTWriter(stream,numTables=len(source.tables),sfntVersion=source.sfntVersion,flavor='woff')
for tag in source.tables:writer[tag]=source[tag]
writer.close();woff=stream.getvalue();converted=SFNTReader(BytesIO(woff))
tables={tag:{'sourceSha256':sha256(source[tag]).hexdigest(),'woffSha256':sha256(converted[tag]).hexdigest(),'exact':source[tag]==converted[tag]} for tag in source.tables}
if not all(record['exact'] for record in tables.values()):raise ValueError('woff_raw_table_changed')
output=Path('artifacts/task-020/font-container/PingFang SC-Semibold-raw.woff');output.write_bytes(woff)
proof={'status':'PASS','scope':'same_authorized_font_container','sourcePath':str(SOURCE),'sourceSha256':EXPECTED,'woffSha256':sha256(woff).hexdigest(),'tables':tables,'programSha256':sha256(Path(__file__).read_bytes()).hexdigest(),'nativeFidelity':'NOT_RUN'}
Path('adapters/penpot/metadata/headed-table-native/semibold-container-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','woffSha256':proof['woffSha256'],'exactRawTables':len(tables)}))
