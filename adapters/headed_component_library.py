"""Explicit headed-table release loader; the frozen 0.2.1 loader stays unchanged."""
import importlib.util
import sys
from adapters.component_bindings import ComponentBindings
from adapters.component_library_versions import load as load_base
from adapters.headed_table import require
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash

def load(version):
    require(version=='0.3.0','unsupported_headed_library_release')
    load_base('0.2.1')
    directory=ROOT/'releases/component-library-0.3.0'
    manifest=load_json(directory/'manifest.json')
    require(manifest['status']=='PASS' and manifest['libraryVersion']==version,'invalid_headed_release')
    for relative,sha in manifest['files'].items():
        path=(ROOT/relative).resolve()
        require(path.is_relative_to(ROOT) and file_hash(path)==sha,'headed_release_file_changed:'+relative)
    spec=importlib.util.spec_from_file_location('ui_design_components_0_3_0',directory/'core/component-resolver/registry.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    registry=module.ComponentRegistry(load_json(directory/'catalog.json'),load_json(directory/'fidelity-reports.json'))
    bindings={p:ComponentBindings(load_json(ROOT/f'adapters/{p}/metadata/component-library-0.3.0/component-bindings.json'),registry,platform=p) for p in ('figma','penpot')}
    return registry,bindings
