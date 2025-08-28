import yaml, typing

def represent_none(self, _):
    return self.represent_scalar('tag:yaml.org,2002:null', '')

yaml.add_representer(type(None), represent_none)

def load_file(fn):
    with open(fn, 'r') as f:
        return yaml.safe_load(f)

# deep merge two dictionaries created from yaml
# when merging primitives, the one from d2 is preferred
def deep_merge(d1, d2, conflicts="new", path=""):
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
        if type(v) != type(result[k]):
            if conflicts == "new":
                result[k] = v
            elif conflicts == "err":
                raise KeyError(f"Multiple entries found for key: {path}.{k}")
            continue
        if isinstance(v, dict):
            result[k] = deep_merge(result[k], v, conflicts, path + "." + k)
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
