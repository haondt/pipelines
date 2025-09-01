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
from ..lib.transform import Transformation
from ..lib.environment import Environment
from ..build import encrypt
from .utils import load_existing_file, parse_bool_env_var
import tempfile
import shutil, re

DEBUG = parse_bool_env_var('DEBUG')

# copy everything except *.haondt.yml
def cp_app_files(project, app, destination_dir):
    def ignore(dir, files):
        # note that  "files" will include subdirectories by name, since everything is a file
        ignored = []
        ignore_regexes = [
            fr'^{project}\/services\/{app}\/[^\/]*\.haondt\.yml$'
        ]
        for file in files:
            path = os.path.join(dir, file)
            for rx in ignore_regexes:
                if re.match(rx, path):
                    ignored.append(file)
        return ignored

    src = os.path.join(project, 'services', app)
    dst = os.path.join(destination_dir)
    shutil.copytree(src, dst, ignore=ignore)

def created_compiled_app_files(project, app, env: Environment, destination_dir):
    # copy files
    cp_app_files(project, app, destination_dir)

    # hydrate
    if os.path.isfile(f'{project}/services/{app}/hydrate.haondt.yml'):
        to_hydrate = load_yaml_file(f'{project}/services/{app}/hydrate.haondt.yml')
        for fn in to_hydrate:
            fn = fn.strip()
            src = os.path.join(project, 'services', app, fn)
            dst = os.path.join(destination_dir, fn)
            data = load_existing_file(src)
            hydrated = hydrate_string(data, env, debug=DEBUG)
            with open(dst, 'w') as sf:
                sf.write(hydrated)
    # transform
    transform_file_path = f'{project}/services/{app}/transform.haondt.yml'
    # transforms are done in place
    transform_context_path = os.path.join(destination_dir)
    if os.path.isfile(transform_file_path):
        transformation_config = load_yaml_file(transform_file_path)
        print(transform_context_path)
        transform = Transformation(transform_context_path, transformation_config, env, debug=DEBUG)
        transform.perform_transformations()


def main():
    parser = argparse.ArgumentParser(prog='docker-build')
    parser.add_argument('app', help='app to build')
    parser.add_argument('project', help='project to build')
    args = parser.parse_args()

    encryption_key = os.environ['GITLAB_DOCKER_BUILD_ENCRYPTION_KEY']

    app = build_vars(args.project, args.app)

    app_def = AppDefinition.model_validate(app.dict)

    with tempfile.TemporaryDirectory() as td:
        # copy and hydrate files
        compiled_file_dir = os.path.join(td, 'compiled_files')
        created_compiled_app_files(args.project, args.app, app.env, compiled_file_dir)

        manifests = create_manifests(app_def, app.env, compiled_file_dir)
        manifests_string = ''
        for manifest in manifests:
            manifests_string += '---\n'
            manifests_string += yaml.dump(manifest, default_flow_style=False) + '\n'

        manifests_file_path = os.path.join(td, f'{args.project}-{args.app}.yml')
        tar_file_path = os.path.join(td, f'{args.project}-{args.app}.tar.gz')
        output_file_path = f'{args.project}-{args.app}.enc'

        with open(manifests_file_path, 'w') as f:
            f.write(manifests_string)
        tar_tools.tar(manifests_file_path, tar_file_path)
        encrypt(encryption_key, tar_file_path, output_file_path)


if __name__ == '__main__':
    if DEBUG:
        main()
    else:
        try:
            main()
        # discard stack trace
        except Exception as e:
            print(f"{type(e).__name__}:", e, file=sys.stderr)
            exit(1)

