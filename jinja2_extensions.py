import re

def setup_filters(env):
    env.filters['regex_ismatch'] = regex_ismatch

def regex_ismatch(value='', pattern='', ignorecase=False):
    ''' Perform a `re.sub` returning a string '''
    if ignorecase:
        flags = re.I
    else:
        flags = 0
    _re = re.compile(pattern, flags=flags)
    match = _re.match(value)
    return bool(match)


