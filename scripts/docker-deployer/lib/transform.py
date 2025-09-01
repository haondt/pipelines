import os, yaml, json

from .hydration import hydrate_string
from .environment import Environment

from .yaml_tools import valueType, containerType, to_flat_dict


class Transformation:
    def __init__(self, base_path, config, hydration_env: Environment, debug: bool=False):
        self.hydration_env: Environment = hydration_env
        self.tranformations = []
        self.debug = debug

        for ct in config:
            transformation = {}
            src = ct['src']
            transformation['src_path'] = os.path.join(base_path, src['path'])
            transformation['src_type'] = src['type']
            transformation['src_hydrate'] = 'hydrate' in src and (src['hydrate'] == True)
            
            dst = ct['dst']
            transformation['dst_path'] = os.path.join(base_path, dst['path'])
            transformation['dst_type'] = dst['type']
            if 'separator' in dst:
                dst_sep = dst['separator']
                if dst_sep is None:
                    dst_sep = ""
                transformation['dst_sep'] = str(dst_sep)

            self.tranformations.append(transformation)

    def _load_source(self, index):
        transformation = self.tranformations[index]
        src_type = transformation['src_type']
        src_string = ""
        with open(transformation['src_path'], 'r') as f:
            src_string = f.read()

        if transformation['src_hydrate']:
            src_string = hydrate_string(src_string, self.hydration_env, self.debug)


        if src_type == 'yaml':
            return yaml.safe_load(src_string)
        if src_type == 'json':
            return json.loads(src_string)
        raise ValueError(f"unknown transformation source: '{src_type}'")

    def _delete_source(self, index):
        transformation = self.tranformations[index]
        src_path = transformation['src_path']
        os.remove(src_path)

    def _write_destination(self, index, data):
        transformation = self.tranformations[index]
        dst_type = transformation['dst_type']

        dst_string = ""
        if dst_type == 'yaml':
            dst_string = yaml.dump(data)
        elif dst_type == 'json':
            dst_string = json.dumps(data, indent=4)
        elif dst_type == 'env':
            if 'dst_sep' in transformation:
                dst_string = to_env(data, transformation['dst_sep'])
            else:
                dst_string = to_env(data)
        else:
            raise ValueError(f"unknown transformation source: '{dst_type}'")

        with open(transformation['dst_path'], 'w') as f:
            f.write(dst_string)


    def perform_transformations(self):
        for i, transformation in enumerate(self.tranformations):
            data = self._load_source(i)
            self._write_destination(i, data)
            self._delete_source(i)


def to_env(data: valueType | containerType, nesting_seperator='__') -> str:
    env_data = to_flat_dict(data, nesting_seperator)
    return '\n'.join([f'{k}="{v}"' for k,v in env_data.items()]) + '\n'
