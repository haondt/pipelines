import re

def regex_ismatch(value='', pattern='', ignorecase=False):
    ''' Perform a `re.sub` returning a string '''
    if ignorecase:
        flags = re.I
    else:
        flags = 0
    _re = re.compile(pattern, flags=flags)
    match = _re.match(value)
    return bool(match)


def try_get_version(tag: str):
    if not regex_ismatch(tag, r'^v\d+\.\d+\.\d+$'):
        return None
    return tag[1:]

# deep merge two dictionaries created from yaml
# when merging primitives, the one from d2 is preferred
def deep_merge(d1, d2, conflicts="new", path=""):
    if conflicts not in ["new", "old", "err"]:
        raise ValueError("Unexpected conflict resolution:" + conflicts)
    def merge_list(l1, l2): #TODO: this should also verify relative ordering of steps
        added = set()
        l = []
        def add_to_l(la):
            nonlocal added
            nonlocal l
            for v in la:
                if v not in added:
                    added.add(v)
                    l.append(v)
        add_to_l(l1)
        add_to_l(l2)
        return l
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


