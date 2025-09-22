import yaml, typing, os, re
from .models import ProjectTypeEnum, StatusEnum
from typing import Any

def represent_none(dumper, _):
    return dumper.represent_scalar('tag:yaml.org,2002:null', '')

def represent_set_as_list(dumper, data):
    return dumper.represent_list(list(data))

def _represent_enum(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.value)

def _represent_str(dumper, data):
    """
        configures yaml for dumping multiline strings
        Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data

        I am intentionally not stripping trailing newlines, meaning if you have them it will go back to the default style. I am doing this in order to avoid changing the contents of the string in any way.
    """
    
    if data.count('\n') > 0:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(StatusEnum, _represent_enum)
yaml.add_representer(ProjectTypeEnum, _represent_enum)
yaml.add_representer(type(None), represent_none)
yaml.add_representer(set, represent_set_as_list)
yaml.add_representer(str, _represent_str)

def unflatten(obj, sep: str = ".",
    conflict="error",
    blacklist_re: str | list[str] | None = None,
    _current_path="") -> Any:
    if conflict not in ["ignore", "overwrite", "error"]:
        raise ValueError("Unexpected conflict resolution:" + conflict)

    blacklist_patterns = []
    if blacklist_re is not None:
        if isinstance(blacklist_re, str):
            blacklist_patterns = [re.compile(blacklist_re)]
        elif isinstance(blacklist_re, list):
            blacklist_patterns = [re.compile(pattern) for pattern in blacklist_re]

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            current_item_path = f"{_current_path}.{key}"
            value = unflatten(value, sep, conflict, blacklist_re, _current_path=current_item_path)
            if not isinstance(key, str):
                result[key] = value
                continue

            if any(pattern.search(current_item_path) for pattern in blacklist_patterns):
                result[key] = value
                continue

            parts = key.split(sep)
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    if conflict == "error":
                        raise ValueError(f"Conflict at {'.'.join(parts[:-1])}")
                    elif conflict == "overwrite":
                        current[part] = {}
                    elif conflict == "ignore":
                        current = None
                        break
                current = current[part]
            if current is not None:
                leaf = parts[-1]
                if leaf in current:
                    if conflict == "error":
                        raise ValueError(f"Conflict at {key}")
                    elif conflict == "overwrite":
                        current[leaf] = value
                    elif conflict == "ignore":
                        continue
                else:
                    current[leaf] = value
        return result
    elif isinstance(obj, list):
        return [unflatten(item, sep, conflict, blacklist_re, _current_path=_current_path + "[]") for item in obj]
    else:
        return obj

def load_existing_file(fn):
    if os.path.isfile(fn):
        with open(fn, 'r') as f:
            return f.read()
    raise ValueError(f"Could not find file {fn}")

def load_file(fn, 
    expand_dot_keys=False,
    expansion_conflict_strategy="err",
    assert_exists: bool=True) -> Any:
    if not os.path.isfile(fn):
        if assert_exists:
            raise ValueError(f"Could not find file {fn}")
        return None

    with open(fn, 'r') as f:
        data = yaml.safe_load(f)
    if expand_dot_keys:
        data = unflatten(data, conflict=expansion_conflict_strategy)
    return data

# deep merge two dictionaries created from yaml
# when merging primitives, the one from d2 is preferred
def deep_merge(d1, d2, conflicts="new", path="", overwrite_with_none=True):
    if conflicts not in ["new", "old", "err"]:
        raise ValueError("Unexpected conflict resolution:" + conflicts)
    def merge_list(l1, l2):
        l3 = []
        added = set()
        for item in l1 + l2:
            if isinstance(item, typing.Hashable):
                if item in added:
                    continue
                added.add(item)
            l3.append(item)
        return l3
    result = d1.copy()
    for k, v in d2.items():
        if k not in result:
            result[k] = v
            continue
        if v is None:
            if not overwrite_with_none:
                continue
        if type(v) != type(result[k]):
            if conflicts == "new":
                result[k] = v
            elif conflicts == "err":
                raise KeyError(f"Multiple entries found for key: {path}.{k}")
            continue
        if isinstance(v, dict):
            result[k] = deep_merge(result[k], v, conflicts, path + "." + k, overwrite_with_none=overwrite_with_none)
            continue
        if isinstance(v, (tuple, list)):
            result[k] = merge_list(result[k], v)
            continue

        if conflicts == "new":
            result[k] = v
        elif conflicts == "err":
            raise KeyError(f"Multiple entries found for key: {path}.{k}")
    return result

valueType = str|int|float|bool
containerType = list[valueType]|dict[str,valueType]


def to_flat_dict(data: valueType | containerType, nesting_seperator='__') -> dict[str, str]:
    def stringify(v: valueType):
        if isinstance(v, str):
            return v
        elif isinstance(v, bool):
            return str(v).lower()
        elif (
            isinstance(v, int) or \
            isinstance(v, float)):
            return str(v)
        raise Exception(f'Cannot convert value \'{v}\'')

    def flatten(prefix, data: valueType | containerType) -> dict[str, str]:
        if isinstance(data, valueType):
            try:
                return { prefix: stringify(data) }
            except:
                raise Exception(f'Cannot convert value for key \'{prefix}\'')
        if len(prefix) > 0:
            prefix = f'{prefix}{nesting_seperator}'
        if isinstance(data, list):
            items = [flatten(f'{prefix}{i}', v) for i, v in enumerate(data)]
            return { k: v for fl in items for k, v in fl.items() }
        if isinstance(data, dict):
            items = [flatten(f'{prefix}{k}', v) for k, v in data.items()]
            return { k: v for fl in items for k, v in fl.items() }
        return {}

    return flatten('', data)

