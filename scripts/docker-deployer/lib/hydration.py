import re
from .environment import Environment

# replace {{ KEY }} with VALUE from d
def hydrate_string(s: str, env: Environment, debug: bool=False):
    def rpl(match):
        k = match.group(1).strip()
        if debug:
            return k
        return env.get_value(k)
    p = re.compile(r"{{\s*([^{}\s]+)\s*}}")
    return re.sub(p, rpl, s)
