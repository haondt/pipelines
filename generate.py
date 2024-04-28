import yaml
from jinja2 import Environment, FileSystemLoader
from jinja2_extensions import setup_filters
from helpers import docker_build, python_build
import os

def load_file(fn):
    with open(fn, 'r') as f:
        return f.read()

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
        'CI_PIPELINE_SOURCE'
        ]:
        if key in private_env:
            env[key] = private_env[key]
    return env

def generate_steps(data):
    tasks = data.get('tasks', [])

    env = get_env()
    output = []
    for task in tasks:
        task_type = task.get('type')

        if task_type == 'docker-build':
            template = get_jinja().get_template('docker-build.yml.jinja')
            rendered = template.render(helpers=docker_build, task=task, env=env)
            output.append(rendered)
        if task_type == 'python-build':
            template = get_jinja().get_template('python-build.yml.jinja')
            rendered = template.render(helpers=python_build, task=task, env=env)
            output.append(rendered)

    return '\n'.join(output)

def deduplicate_keys(yaml_data: str):
    data = yaml.safe_load(yaml_data)
    return yaml.dump(data)

def main():
    public_env = get_public_env()
    for k, v in public_env.items():
        print(f'# {k}: {v}')

    pipeline_file = 'pipeline.yml'
    data = load_yaml(pipeline_file)
    steps = generate_steps(data)
    dd_steps = deduplicate_keys(steps)

    print(dd_steps)

if __name__ == '__main__':
    main()
