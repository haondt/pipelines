import argparse, yaml, os, sys
from ..lib.environment import Environment
from ..lib.yaml_tools import deep_merge, load_file as load_yaml_file
from ..lib.hydration import hydrate_string
from .create_manifests import create_manifests
from .models import AppDefinition
from types import SimpleNamespace
from datetime import datetime, timezone
from .build_vars import build_vars
from ..lib import tar_tools
from ..build import encrypt
import tempfile



def main():
    parser = argparse.ArgumentParser(prog='docker-build')
    parser.add_argument('app', help='app to build')
    parser.add_argument('project', help='project to build')
    args = parser.parse_args()

    encryption_key = os.environ['GITLAB_DOCKER_BUILD_ENCRYPTION_KEY']

    app = build_vars(args.project, args.app)

    try:
        app_def = AppDefinition.model_validate(app.dict)
    except Exception as e:
        raise ValueError(f"Failed to validate app YAML structure: {e}")

    manifests = create_manifests(app_def, app.env)
    manifests_string = ''
    for manifest in manifests:
        manifests_string += '---\n'
        manifests_string += yaml.dump(manifest) + '\n'

    with tempfile.TemporaryDirectory() as td:
        manifests_file_path = os.path.join(td, f'{args.project}-{args.app}.yml')
        tar_file_path = os.path.join(td, f'{args.project}-{args.app}.tar.gz')
        output_file_path = f'{args.project}-{args.app}.enc'

        with open(manifests_file_path, 'w') as f:
            f.write(manifests_string)
        tar_tools.tar(manifests_file_path, tar_file_path)
        encrypt(encryption_key, tar_file_path, output_file_path)

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)

