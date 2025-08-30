import argparse, yaml, os, sys
from ..lib.environment import Environment
from ..lib.yaml_tools import deep_merge, load_file as load_yaml_file
from ..lib.hydration import hydrate_string
from types import SimpleNamespace
from datetime import datetime, timezone

COMPONENT_KEY = 'COM_HAONDT_COMPONENT'

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

def build_app_yaml(project, app_dir_name, base_env: Environment, app_base_yaml: str | None, component_base_yaml: str | None):
    # create environment
    app_env = Environment()
    app_env.load_plugin_yaml_file(f"{project}/services/{app_dir_name}/env.haondt.yml", True)

    # merge environment with base
    app_env = base_env.combine(app_env)

    # load app yaml
    app_yaml = load_existing_file(f"{project}/services/{app_dir_name}/kubernetes.haondt.yml")

    # hydrate and load app_yaml
    app_hydrated = hydrate_string(app_yaml, app_env)
    app_loaded = yaml.safe_load(app_hydrated)
    
    # hydrate and load app_base_yaml
    if app_base_yaml is not None:
        app_base_hydrated = hydrate_string(app_base_yaml, app_env)
        app_base_loaded = yaml.safe_load(app_base_hydrated)
        app_loaded = deep_merge(app_base_loaded, app_loaded)


    # get components in app
    if component_base_yaml is not None:
        components = app_loaded['spec']['components'].keys()
        for component in components:
            # hydrate component_base_yaml with component name and app + base environment
            component_env = app_env.copy()
            component_env.add_value(COMPONENT_KEY, component, overwrite=True)
            component_base_hydrated = hydrate_string(component_base_yaml, component_env)
            component_base_loaded = yaml.safe_load(component_base_hydrated)

            # merge component base yaml into app yaml
            app_loaded = deep_merge(component_base_loaded, app_loaded)

            # parse docker image
            docker_image = app_loaded.get('spec', {}) \
                .get('components', {}) \
                .get(component, {}) \
                .get('spec', {}) \
                .get('image')
            docker_image_version = None
            docker_image_name = None
            if  docker_image is not None:
                docker_image_name, docker_image_version = parse_docker_image(docker_image)

            # add defaults
            component_static_config = get_static_default_component_yaml(
                component,
                component_env,
                docker_image_version,
                docker_image_name)
            app_loaded = deep_merge(component_static_config, app_loaded)

    # get static config
    app_static_config = get_static_default_app_yaml(project, app_dir_name, app_env)
    app_loaded = deep_merge(app_static_config, app_loaded)

    return SimpleNamespace(dict=app_loaded, env=app_env)

def parse_docker_image(spec: str) -> tuple[str | None, str | None]:
    digest = None
    if '@' in spec:
        spec, digest = spec.split('@', 1)
    if ':' in spec:
        name, tag = spec.rsplit(':', 1)
    else:
        name, tag = spec, None
    if digest:
        tag = f"{tag or ''}@{digest}"
    return name, tag

def get_static_default_app_yaml(project_name: str, app_dir_name: str, app_env: Environment) -> dict:
    return {
        'metadata': {
            'name': app_dir_name,
            'namespace': app_dir_name,
            'labels': {
                'deployment.haondt.dev/managed-by': 'haondt-docker-deployer',
                'app.kubernetes.io/managed-by': 'haondt-docker-deployer',
                'deployment.haondt.dev/part-of': project_name,
                'app.kubernetes.io/part-of': project_name,
            },
            'annotations': {
                'deployment.haondt.dev/timestamp': datetime.now(timezone.utc).isoformat(),
                'deployment.haondt.dev/commit': os.environ['CI_COMMIT_SHA']
            }
        }
    }

def get_static_default_component_yaml(component_name: str, component_env: Environment, version: str | None, image: str | None) -> dict:
    result = {
        'metadata': {
            'labels': {
                'deployment.haondt.dev/name': component_name,
                'app.kubernetes.io/name': component_name,
            },
            'annotations': {
            }
        }
    }

    if version is not None:
        result['metadata']['annotations']['deployment.haondt.dev/version'] = version
        result['metadata']['annotations']['app.kubernetes.io/version'] = version
    if image is not None:
        result['metadata']['annotations']['deployment.haondt.dev/image'] = image

    return {
        'spec': {
            'components': {
                component_name: result
            }
        }
    }

def main():
    parser = argparse.ArgumentParser(prog='docker-build')
    parser.add_argument('app', help='project to build')
    parser.add_argument('project', help='project to build')
    args = parser.parse_args()

    encryption_key = os.environ['GITLAB_DOCKER_BUILD_ENCRYPTION_KEY']

    project = args.project
    base_env = Environment()
    base_env.load_plugin_yaml_file(os.path.join(project, "env.haondt.yml"), True)
    app_base_yaml = load_file(os.path.join(project, 'kubernetes-app-base.haondt.yml'))
    component_base_yaml = load_file(os.path.join(project, 'kubernetes-component-base.haondt.yml'))
    app_yaml = build_app_yaml(project, args.app, base_env, app_base_yaml, component_base_yaml) 

    # app_yaml.dict.setdefault('metadata', {}).setdefault('namespace', args.app)
    # app_yaml.dict['metadata'].setdefault('name', args.app)


    print(yaml.dump(app_yaml.dict))

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)

