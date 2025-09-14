import os, hashlib, re, json

from pydantic import BaseModel

def load_file(fn):
    if os.path.isfile(fn):
        with open(fn, 'r') as f:
            return f.read()
    return None

def load_existing_file(fn):
    if os.path.isfile(fn):
        with open(fn, 'r') as f:
            return f.read()
    raise ValueError(f"Could not find file {fn}")



def parse_env_string(s: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in s.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid line: {line}")
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result

def hash_str(s: str, length: int = 12) -> str:
    h = hashlib.sha256(s.encode('utf-8')).hexdigest()
    return h[:length]

def generate_stable_id(m: BaseModel, length: int = 8) -> str:
    d = m.model_dump(mode="json")
    j = json.dumps(d, sort_keys=True)
    return hash_str(j, length)

def make_config_map_key(path: str) -> str:
    safe = re.sub(r'[^A-Za-z0-9.\-_]', '__', path)
    h = hash_str(path, 8)
    return f"{safe}-{h}"

def coerce_dns_name(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^a-z0-9-]', '-', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    s = s[:253]
    s = s.strip('-')
    return s
