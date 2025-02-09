import yaml, argparse
from jinja2 import Environment, FileSystemLoader
from jinja2_extensions import setup_filters
from helpers import docker_build, python_build, docker_deploy, dotnet_build, docker_deploy_v2
import os
import functools

@functools.cache
def get_images():
    return {
        'docker': 'docker:27.5.1',
        'hephaestus': 'registry.gitlab.com/haondt/cicd/registry/hephaestus:1.0.1',
        'docker_deployer': 'registry.gitlab.com/haondt/cicd/registry/docker-deployer:1.1.8',
        'docker_deployer_v2': 'registry.gitlab.com/haondt/cicd/registry/docker-deployer:2.1.1',
        'python': 'registry.gitlab.com/haondt/cicd/registry/python-builder:2.0.1',
        'docs': 'registry.gitlab.com/haondt/cicd/registry/docs-builder:1.0.4',
        'dotnet': 'registry.gitlab.com/haondt/cicd/registry/dotnet-builder:0.0.2',
    }

def load_file(fn):
    with open(fn, 'r') as f:
        return f.read()

def load_pipeline_config():
    pipeline_file = 'pipeline.yml'
    data = load_yaml(pipeline_file)
    if 'tasks' not in data:
        data['tasks'] = []
    for i in range(len(data['tasks'])):
        data['tasks'][i]['index'] = i
    return data

def load_yaml(fn):
    with open(fn, 'r') as f:
        return yaml.safe_load(f)

_jinja_env = None
def get_jinja():
    global _jinja_env
    if _jinja_env is None:
        env = Environment(loader=FileSystemLoader('templates'))
        setup_filters(env)
        _jinja_env = env
    return _jinja_env

_env: dict[str, str] | None = None
def get_env():
    global _env
    if _env is None:
        env = {}
        def cpy(key):
            nonlocal env
            env[key] = os.environ[key]
        def trycpy(key):
            nonlocal env
            if key in os.environ:
                env[key] = os.environ[key]

        cpy('GITLAB_CR_REGISTRY')
        cpy('DOCKER_HUB_REPOSITORY')

        trycpy('CI_COMMIT_TAG')
        trycpy('CI_COMMIT_BRANCH')
        cpy('CI_COMMIT_SHORT_SHA')
        cpy('ROOT_PIPELINE_SOURCE')
        cpy('CI_PIPELINE_SOURCE')

        _env = env

    return _env

def get_public_env():
    private_env = get_env()
    env = {}
    for key in [
        'GITLAB_CR_REGISTRY',
        'DOCKER_HUB_REPOSITORY',
        'CI_COMMIT_TAG',
        'CI_COMMIT_BRANCH',
        'CI_COMMIT_SHORT_SHA',
        'ROOT_PIPELINE_SOURCE'
        'CI_PIPELINE_SOURCE'
        ]:
        if key in private_env:
            env[key] = private_env[key]
    return env

def render_template(env, xtra, task, task_type = None):
    task_type = task_type or task.get('type')

    if task_type == 'docker-build':
        template = get_jinja().get_template('docker-build.yml.jinja')
        return template.render(helpers=docker_build, task=task, env=env, images=get_images())
    if task_type == 'python-build':
        template = get_jinja().get_template('python-build.yml.jinja')
        return template.render(helpers=python_build, task=task, env=env, images=get_images())
    if task_type == 'docker-deploy':
        template = get_jinja().get_template('docker-deploy.yml.jinja')
        return template.render(helpers=docker_deploy, task=task, env=env, images=get_images(), xtra=xtra)
    if task_type == 'docker-deploy-v2':
        template = get_jinja().get_template('docker-deploy-v2.yml.jinja')
        return template.render(helpers=docker_deploy_v2, task=task, env=env, images=get_images(), xtra=xtra)
    if task_type == 'noop':
        template = get_jinja().get_template('noop.yml.jinja')
        return template.render()
    if task_type == 'docker-deploy-downstream':
        template = get_jinja().get_template('docker-deploy-downstream.yml.jinja')
        return template.render(helpers=docker_deploy, task=task, env=env, images=get_images())
    if task_type == 'docker-deploy-downstream-v2':
        template = get_jinja().get_template('docker-deploy-downstream-v2.yml.jinja')
        return template.render(helpers=docker_deploy_v2, task=task, env=env, images=get_images(), xtra=xtra)
    if task_type == 'docs':
        template = get_jinja().get_template('docs.yml.jinja')
        return template.render(task=task, env=env, images=get_images())
    if task_type == 'dotnet-build':
        template = get_jinja().get_template('dotnet-build.yml.jinja')
        return template.render(helpers=dotnet_build, task=task, env=env, images=get_images())
    raise ValueError(f"unknown task type: {task_type}")

def deduplicate_keys(yaml_data: str):
    data = yaml.safe_load(yaml_data)
    return yaml.dump(data)

def main():
    parser = argparse.ArgumentParser(prog='render-build')
    parser.add_argument('task_index', help='index of task to render for')
    parser.add_argument('template', help='template to render', choices=[
        'docker-build',
        'python-build',
        'docker-deploy',
        'docker-deploy-downstream',
        'docker-deploy-v2',
        'docker-deploy-downstream-v2',
        'docs',
        'noop'
        ])
    parser.add_argument('-x', '--xtra', action='append', help='extra args (key=value) to pass to the template renderer', type=str)
    args = parser.parse_args()
    template_name = args.template
    task_i = args.task_index
    xtra = {}
    if args.xtra is not None:
        for pair in args.xtra:
            key, value = pair.split('=')
            xtra[key] = value

    data = load_pipeline_config()
    task = data['tasks'][int(task_i)]

    env = get_env()
    public_env = get_public_env()
    for k, v in public_env.items():
        print(f'# {k}: {v}')


    rendered = render_template(env, xtra, task, template_name)
    dd_rendered = deduplicate_keys(rendered)

    print(dd_rendered)

if __name__ == '__main__':
    main()
