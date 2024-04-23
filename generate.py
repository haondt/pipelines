import yaml
from jinja2 import Template
import os

def load_file(fn):
    with open(fn, 'r') as f:
        return f.read()

def load_yaml(fn):
    with open(fn, 'r') as f:
        return yaml.safe_load(f)

def load_template(fn):
    file = load_file(fn)
    return Template(file)

def load_environment():
    env = {}
    def cpy(key):
        nonlocal env
        env[key] = os.environ[key]

    cpy('GITLAB_CR_REGISTRY')
    cpy('DOCKER_HUB_REPOSITORY')

    return env

def generate_steps(data, env):
    tasks = data.get('tasks', [])

    output = []
    for task in tasks:
        task_type = task.get('type')

        if task_type == 'docker-build':
            template = load_template('templates/docker-build.yml.jinja')
            rendered = template.render(task=task, env=env)
            output.append(rendered)

    return '\n'.join(output)

def main():
    for var in [
            'CI_COMMIT_TAG',
            'CI_COMMIT_TAG_MESSAGE',
            'CI_COMMIT_SHA',
            'CI_COMMIT_SHORT_SHA',
            'CI_COMMIT_REF_NAME',
            'CI_COMMIT_REF_SLUG',
            'CI_COMMIT_BRANCH',
            'CI_PIPELINE_SOURCE'
            ]:
        print(f"{var}: {os.environ.get(var, 'does not exist')}")
    pipeline_file = 'pipeline.yml'
    data = load_yaml(pipeline_file)
    env = load_environment()
    steps = generate_steps(data, env)

    print(steps)

if __name__ == '__main__':
    main()
