"""Explicit immutable component-library releases; no automatic default migration."""
import importlib.util
from pathlib import Path
import sys
from adapters.component_bindings import ComponentBindings
from adapters.configurable_table import require
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash


def load(version):
    require(version=='0.2.1','unsupported_component_library_release')
    directory=ROOT/'releases'/('component-library-'+version)
    manifest=load_json(directory/'manifest.json')
    require(manifest['status']=='PASS' and manifest['libraryVersion']==version and manifest['scope']=='explicit-component-library-release','invalid_library_release')
    for relative,sha in manifest['files'].items():
        path=(ROOT/relative).resolve();require(path.is_relative_to(ROOT) and file_hash(path)==sha,'library_release_file_changed:'+relative)
    spec=importlib.util.spec_from_file_location('ui_design_components_0_2_1',directory/'core/component-resolver/registry.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    registry=module.ComponentRegistry(load_json(directory/'catalog.json'),load_json(directory/'fidelity-reports.json'))
    bindings={platform:ComponentBindings(load_json(ROOT/f'adapters/{platform}/metadata/component-library-{version}/component-bindings.json'),registry,platform=platform) for platform in ('figma','penpot')}
    return registry,bindings
