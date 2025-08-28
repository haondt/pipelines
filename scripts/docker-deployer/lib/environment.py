from typing import Self
from typing import Callable
import re, os

from .plugins import execute_plugin
from .yaml_tools import load_file as yaml_load_file, to_flat_dict
from .yaml_tools import to_flat_dict

class CachedExecutor:
    def __init__(self, func: Callable[..., str], *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._value: None | str = None
    def execute(self) -> str:
        if self._value is None:
            self._value = self._func(*self._args, **self._kwargs)
        return self._value

class Environment():
    def __init__(self, nesting_seperator='__'):
        self._env: dict[str, Callable[[], str]] = {}
        self.nesting_seperator = nesting_seperator
        self._plugin_args_pattern = re.compile("(?:'([^']*)')|([0-9]+)")

    def add_value(self, key: str, value: Callable[[], str] | str, overwrite=False):
        if key in self._env:
            if not overwrite:
                raise ValueError(f"Multiple entries for variable: {key}")
        if isinstance(value, str):
            self._env[key] = lambda: value
        else:
            self._env[key] = value

    def copy(self):
        output = Environment()
        for k,v in self._env.items():
            output.add_value(k, v)
        return output

    def get_value(self, key: str):
        if key not in self._env:
            raise KeyError(f"Key '{key}' not found in environment")
        return self._env[key]()

    def combine(self, other: Self):
        output = self.copy()
        for k, v in other._env.items():
            output.add_value(k, v)
        return output

    def load_env_file(self, fn):
        base_pattern = re.compile(r'^\s*([^\s#]+)\s*=\s*(?:(?:"([^"\s#]*)")|([^\s#]*))\s*$')
        ignore_pattern = re.compile(r"^\s*(#.*)?$")
        with open(fn, 'r') as f:
            for l in f:
                l = l.strip()
                im = ignore_pattern.match(l)
                if im:
                    continue

                bm = base_pattern.match(l)
                if bm:
                    k, v1, v2 = [i.strip() if i is not None else None for i in bm.groups()]
                    v = v1 or v2
                    if k in self._env:
                        raise ValueError(f"Multiple entries for variable: {k}")
                    if v is not None and k is not None:
                        self._env[k] = lambda: v
                raise ValueError(f"Malformed environment variable: {l}")

    def load_plugin_yaml_file(self, fn, skip_if_dne=False):
        if skip_if_dne and not os.path.isfile(fn):
            return

        data = yaml_load_file(fn)
        data = to_flat_dict(data)

        # this is different than the env file one
        plugin_pattern = re.compile(r"^\s*\{\{\s*([A-Za-z_-]+)\s*\(\s*([^)]*)\s*\)\s*\}\}\s*$")

        for k, v in data.items():
            pm = plugin_pattern.match(v)
            if pm:
                g = [i for i in pm.groups() if i != None]
                args = ([''.join(i) for i in self._plugin_args_pattern.findall(g[1])])
                self.add_value(k, CachedExecutor(execute_plugin, g[0], args).execute)
            else:
                self.add_value(k, v)

    def load_plugin_env_file(self, fn: str, skip_if_dne=False):
        if skip_if_dne and not os.path.isfile(fn):
            return

        plugin_pattern = re.compile(r"^\s*([^\s#]+)\s*=\{\{\s*([A-Za-z_-]+)\s*\(\s*([^)]*)\s*\)\s*\}\}\s*$")
        base_pattern = re.compile(r'^\s*([^\s#]+)\s*=\s*(?:(?:"([^"\s#]*)")|([^\s#]*))\s*$')
        ignore_pattern = re.compile(r"^\s*(#.*)?$")

        with open(fn, 'r') as f:
            for l in f:
                l = l.strip()

                im = ignore_pattern.match(l)
                if im:
                    continue

                pm = plugin_pattern.match(l)
                if pm:
                    g = [i for i in pm.groups() if i != None]
                    args = ([''.join(i) for i in self._plugin_args_pattern.findall(g[2])])
                    self.add_value(g[0], CachedExecutor(execute_plugin, g[1], args).execute)
                    continue

                bm = base_pattern.match(l)
                if bm:
                    k, v1, v2 = [i.strip() if i is not None else None for i in bm.groups()]
                    v = v1 or v2
                    if v is not None and k is not None:
                        self.add_value(k, v)
                        continue
                raise ValueError(f"Malformed environment variable: {l}")

