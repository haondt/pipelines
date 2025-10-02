import os, yaml, shutil, sys, tempfile, re
from pathlib import Path
from types import SimpleNamespace
import argparse

from .lib.environment import Environment
from .lib.hydration import hydrate_string
from .lib.yaml_tools import deep_merge, load_file as load_yaml_file
from .lib.tar_tools import tar, encrypt
from .lib.transform import Transformation
from .lib.configuration import parse_bool_env_var
from .get_changes import build_repo_map
from .get_containers import get_services

CONTAINER_KEY = 'COM_HAONDT_CONTAINER'
DEBUG = parse_bool_env_var('DEBUG')

def load_file(fn):
    with open(fn, 'r') as f:
        return f.read()


def build_service_yaml(project, service, base_env: Environment, base_yaml):
    # create environment
    service_env = Environment()
    service_env.load_plugin_yaml_file(f"{project}/services/{service}/env.haondt.yml", True)

    # merge environment with base
    service_env = base_env.combine(service_env)

    # load service yaml
    service_yaml = load_file(f"{project}/services/{service}/docker-compose.yml")

    # hydrate service_yaml
    service_hydrated = hydrate_string(service_yaml, service_env)

    # get containers in service
    service_loaded = yaml.safe_load(service_hydrated)
    containers = service_loaded['services'].keys()
    for container in containers:
        # hydrate base_yaml with container name and service + base environment
        container_env = service_env.copy()
        container_env.add_value(CONTAINER_KEY, container, overwrite=True)
        container_hydrated = hydrate_string(base_yaml, container_env)
        container_loaded = yaml.safe_load(container_hydrated)

        # merge container description from service into container base yaml
        container_loaded = deep_merge(container_loaded, {'services': { f"{container}": service_loaded['services'][container] } })
        # merge container base yaml into service yaml
        service_loaded = deep_merge(service_loaded, container_loaded)
    return SimpleNamespace(dict=service_loaded, env=service_env)


# copy all service files except the following:
# - services/*/docker-compose.yml
# - *.haondt.yml
# - services/*/*.haondt.yml
def cpy_services(project, destination_dir, services):
    def ignore(dir, files):
        # note that  "files" will include subdirectories by name, since everything is a file
        ignored = []
        ignore_regexes = [
            fr'^{project}\/[^\/]*\.haondt\.yml$'
            fr'^{project}\/services/[^\/]+\/docker-compose.yml$',
            fr'^{project}\/services/[^\/]+\/[^\/]*\.haondt.yml$',
        ]
        for file in files:
            path = os.path.join(dir, file)
            for rx in ignore_regexes:
                if re.match(rx, path):
                    ignored.append(file)
        return ignored

    for svc in services:
        src = os.path.join(project, 'services', svc)
        dst = os.path.join(destination_dir, svc)
        shutil.copytree(src, dst, ignore=ignore)



def build_project(project_map: dict, encryption_key: str, project: str):
    services = set(get_services(project))
    for k, v in project_map['services'].items():
        if v['status'] == 'removed' and k in services:
            services.remove(k)

    # load base files
    base_env = Environment()
    base_env.load_plugin_yaml_file(os.path.join(project, "env.haondt.yml"), True)
    base_yaml = load_file(os.path.join(project, 'docker-compose-base.haondt.yml'))

    # generate config objects for each service
    service_configs = [build_service_yaml(project, s, base_env, base_yaml) for s in services]
    containers = [c for cfg in service_configs for c in cfg.dict['services'].keys()]

    # merge service configs
    service_config = service_configs[0].dict.copy()
    for cfg in service_configs[1:]:
        service_config = deep_merge(service_config, cfg.dict, conflicts="err")

    # create final file
    final_yaml = yaml.dump(service_config, default_flow_style=False)

    # save
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, 'docker-compose.yml'), 'w') as f:
            f.write(final_yaml)
        with open(os.path.join(td, 'changes.txt'), 'w') as f:
            f.write('\n'.join(containers))

        # copy and hydrate extra service files
        cpy_services(project, td, services)
        for (i, service) in enumerate(services):
            if os.path.isfile(f'{project}/services/{service}/hydrate.haondt.yml'):
                to_hydrate = load_yaml_file(f'{project}/services/{service}/hydrate.haondt.yml')
                for fn in to_hydrate:
                    fn = fn.strip()
                    src = os.path.join(project, 'services', service, fn)
                    dst = os.path.join(td, service, fn)
                    data = load_file(src)
                    hydrated = hydrate_string(data, service_configs[i].env)
                    with open(dst, 'w') as sf:
                        sf.write(hydrated)

            # apply transformations
            transform_file_path = f'{project}/services/{service}/transform.haondt.yml'
            transform_context_path = os.path.join(td, service)
            if os.path.isfile(transform_file_path):
                transformation_config = load_yaml_file(transform_file_path)
                transform = Transformation(transform_context_path, transformation_config, service_configs[i].env)
                transform.perform_transformations()

        tar(td, f'{project}.tar.gz')

        encrypt(encryption_key, os.path.join(td, f'{project}.tar.gz'), f'{project}.enc')


def main():
    parser = argparse.ArgumentParser(prog='docker-build')
    parser.add_argument('changes', help='repository map')
    parser.add_argument('project', help='project to build')
    args = parser.parse_args()

    key = os.environ['GITLAB_DOCKER_BUILD_ENCRYPTION_KEY']

    with open(args.changes) as f:
        map = yaml.safe_load(f)

    build_project(map['projects'][args.project], key, args.project)

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

