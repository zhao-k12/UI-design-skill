"""Byte-exact official SVG inventory for the fixed acceptance page."""
import hashlib
from pathlib import Path
from importlib import import_module
from validators.ui_ir import ROOT


def prepare_icons(file_reference,page_reference):
    registry=import_module('core.icon-resolver.registry').IconRegistry(import_module('icon-manager.remix-sync.manager').current())
    if registry.snapshot['scope']!='production':raise ValueError('test_icon_source')
    inventory=[]
    for logical in ('remix.settings-3-line','remix.download-line'):
        descriptor=registry.resolve(logical)['descriptor']
        raw=(ROOT/'registries/icons/objects'/(descriptor['svgSha256']+'.svg')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=descriptor['svgSha256']:raise ValueError('icon_source_changed')
        inventory.append({'iconId':logical,'svgSha256':descriptor['svgSha256'],'svg':raw.decode('utf-8')})
    return {'fileReference':file_reference,'pageReference':page_reference,'registrySha256':registry.fingerprint,'sourceVersion':registry.snapshot['sourceVersion'],'icons':inventory}
