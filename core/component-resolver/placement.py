"""Place admitted source geometry inside an existing layout envelope."""
from copy import deepcopy
import importlib
import math
from pathlib import Path

from jsonschema import Draft202012Validator
from validators.ui_ir import load_json

registry_module = importlib.import_module('core.component-resolver.registry')


class SourceGeometry:
    def __init__(self, bundle, registry):
        schema = load_json(Path(__file__).resolve().parents[2] / 'schemas/component-ir.schema.json')
        Draft202012Validator(schema).validate(bundle)
        self._sizes = {}
        self._components = {}
        self.registry_sha256 = registry.fingerprint
        for component in bundle['components']:
            logical_id, variant = component['logicalComponentId'], component['variant']
            key = (logical_id, variant)
            if key in self._sizes:
                raise ValueError('Duplicate source geometry')
            descriptor = registry.resolve(logical_id, variant)['descriptor']
            if component['componentType'] != descriptor['componentType']:
                raise ValueError('Source component type does not match registry')
            if registry_module.digest(component) != descriptor['fidelity']['componentIrSha256']:
                raise ValueError('Source geometry does not match admitted Component IR')
            bounds = component['rootBounds']
            size = {axis: bounds[axis] for axis in ('width', 'height')}
            if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in size.values()):
                raise ValueError('Source geometry must have finite positive dimensions')
            self._sizes[key] = size
            self._components[key] = deepcopy(component)
        self.fingerprint = registry_module.digest({'registrySha256': self.registry_sha256,
                                                 'sourceBundle': bundle})

    def table_metrics(self, logical_id, variant):
        component = self._components.get((logical_id, variant))
        if not component or component['componentType'] != 'Table':
            raise ValueError('Table metrics require admitted Table geometry')
        nodes = component['nodes']; by_path = {n['path']: n for n in nodes}
        rows = [n for n in nodes if n['tag']=='tr' and n['visible'] and n['bounds']['height']>0
                and by_path[n['parentPath']]['tag']=='tbody']
        if not rows: raise ValueError('Missing measured Table rows')
        row=rows[0];cells=[n for n in nodes if n['tag']=='td' and n['parentPath']==row['path'] and n['visible']]
        roots=[n['bounds'] for n in nodes if n['parentPath'] is None]
        if len(roots)!=1 or roots[0]['width']!=component['rootBounds']['width']:
            raise ValueError('Ambiguous source Table root bounds')
        root=roots[0];widths=[];cursor=root['x']
        for cell in cells:
            bounds=cell['bounds']
            if bounds['x']!=cursor:raise ValueError('Non-contiguous source Table columns')
            end=min(bounds['x']+bounds['width'],root['x']+root['width'])
            if end<=cursor:raise ValueError('Invalid visible Table column')
            widths.append(end-cursor);cursor=end
        if cursor!=root['x']+root['width']:raise ValueError('Incomplete measured Table width')
        return {'widths':widths,'height':row['bounds']['height']}

    def source_component(self, logical_id, variant):
        try:return deepcopy(self._components[(logical_id,variant)])
        except KeyError as exc:raise ValueError('Missing admitted source component') from exc

    def place(self, instance, box):
        """Return a new instance and world box; never resize the source or Cell."""
        size = self._sizes.get((instance['componentId'], instance['variant']))
        if size is None:
            raise ValueError('Missing admitted source geometry for component variant')
        if any(type(box.get(k)) not in (int, float) or not math.isfinite(box[k])
               for k in ('x', 'y', 'width', 'height')):
            raise ValueError('Invalid layout envelope')
        if any(size[axis] > box[axis] for axis in ('width', 'height')):
            raise ValueError('Source component does not fit existing layout envelope')
        node = deepcopy(instance)
        node['layout'] = {axis: {'mode': 'fixed', 'value': size[axis]} for axis in size}
        return {'instance': node, 'instanceBox': {'x': box['x'], 'y': box['y'], **size},
                'cellBox': deepcopy(box), 'sourceGeometrySha256': self.fingerprint}
