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
