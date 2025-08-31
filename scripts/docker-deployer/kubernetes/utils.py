import os
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
