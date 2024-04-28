import yaml
from jinja2 import Environment, FileSystemLoader
from jinja2_extensions import setup_filters
from helpers import docker_build, pypi_build
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

_env = None
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

def generate_steps(data):
    tasks = data.get('tasks', [])

    output = []
    for task in tasks:
        task_type = task.get('type')

        if task_type == 'docker-build':
            template = get_jinja().get_template('docker-build.yml.jinja')
            rendered = template.render(helpers=docker_build, task=task, env=get_env())
            output.append(rendered)
        if task_type == 'pypi-build':
            template = get_jinja().get_template('pypi-build.yml.jinja')
            rendered = template.render(helpers=pypi_build, task=task, env=get_env())
            output.append(rendered)

    return '\n'.join(output)

def main():
    pipeline_file = 'pipeline.yml'
    data = load_yaml(pipeline_file)
    steps = generate_steps(data)

    print(steps)

if __name__ == '__main__':
    main()
