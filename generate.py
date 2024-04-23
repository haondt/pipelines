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
        #on = task.get('on')

        if task_type == 'docker-build':
            template = load_template('templates/docker-build.yml.jinja')
            rendered = template.render(task=task, env=env)
            output.append(rendered)

    return '\n'.join(output)

def main():
    pipeline_file = 'pipeline.yml'
    data = load_yaml(pipeline_file)
    env = load_environment()
    steps = generate_steps(data, env)
    print(steps)

if __name__ == '__main__':
    main()
