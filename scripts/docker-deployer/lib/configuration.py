import os
def parse_bool_env_var(var_name, default=False):
    value = os.getenv(var_name)
    if value is not None:
        value_str = str(value).lower()
        return value_str in ('true', '1') or \
               (value_str.isdigit() and int(value_str) != 0)
    return default
