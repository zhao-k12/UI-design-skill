"""Existing local business images only; never generate replacement artwork."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from PIL import Image
from jsonschema import Draft202012Validator
from validators.ui_ir import ROOT, load_json

KINDS=('logo','avatar','photo','banner','illustration','background','empty-state')


class AssetError(ValueError):
    def __init__(self, code, message):
        self.code=code
        super().__init__(message)


def inspect(descriptor, source_root):
    """Read a declared file within its root, checking exact bytes and dimensions."""
    Draft202012Validator(load_json(ROOT/'schemas/asset-registry.schema.json')['$defs']['asset']).validate(descriptor)
    root=Path(source_root).resolve();relative=Path(descriptor['path']);path=(root/relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root):
        raise AssetError('invalid_asset','Asset path escapes its declared source root')
    try:raw=path.read_bytes()
    except OSError as exc:raise AssetError('missing_asset','Declared asset file is unavailable') from exc
    if sha256(raw).hexdigest()!=descriptor['sha256']:
        raise AssetError('invalid_asset','Asset bytes differ from the frozen source')
    try:
        with Image.open(BytesIO(raw)) as image:
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            media={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}.get(image.format)
            if image.size!=(descriptor['width'],descriptor['height']) or media!=descriptor['mediaType'] or getattr(image,'n_frames',1)!=1:
                raise AssetError('invalid_asset','Asset media or dimensions differ from the declared static source')
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        if isinstance(exc,AssetError):raise
        raise AssetError('invalid_asset','Asset is not a complete supported static image') from exc
    return deepcopy(descriptor)


class AssetRegistry:
    def __init__(self, data, source_root):
        Draft202012Validator(load_json(ROOT/'schemas/asset-registry.schema.json')).validate(data)
        ids=[a['assetId'] for a in data['assets']]
        if len(ids)!=len(set(ids)):raise AssetError('invalid_asset','Duplicate asset identity')
        self._data=deepcopy(data);self.source_root=Path(source_root).resolve()
        self.fingerprint=sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    @property
    def snapshot(self):return deepcopy(self._data)

    def resolve(self, asset_id, *, prototype_assets=None, prototype_root=None):
        candidates=prototype_assets or []
        ids=[a['assetId'] for a in candidates]
        if len(ids)!=len(set(ids)):raise AssetError('invalid_asset','Duplicate prototype asset identity')
        matches=[a for a in candidates if a['assetId']==asset_id]
        if matches:
            if prototype_root is None:raise AssetError('invalid_asset','Prototype assets require their declared source root')
            return {'origin':'prototype','descriptor':inspect(matches[0],prototype_root)}
        matches=[a for a in self._data['assets'] if a['assetId']==asset_id]
        if not matches:raise AssetError('missing_asset','No existing prototype or registered asset: '+asset_id)
        return {'origin':'registry','descriptor':inspect(matches[0],self.source_root)}
