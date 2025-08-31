import argparse
import os, sys
import tempfile
from .lib.tar_tools import untar, decrypt

def main():
    parser = argparse.ArgumentParser(prog='untar')
    parser.add_argument('project', help='project name')
    parser.add_argument('output', help='output path')
    args = parser.parse_args()
    encryption_key = os.environ['GITLAB_DOCKER_BUILD_ENCRYPTION_KEY']
    project = args.project
    with tempfile.TemporaryDirectory() as td:
        tf = os.path.join(td, f'{project}.tar.gz')
        decrypt(encryption_key, f'{project}.enc', tf)
        untar(tf, args.output)

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)
