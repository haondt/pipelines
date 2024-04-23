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

def generate_steps(data):
    tasks = data.get('tasks', [])

    output = []
    for task in tasks:
        task_type = task.get('type')
        #on = task.get('on')

        if task_type == 'docker-build':
            registry = task.get('registry', 'gitlab')
            registry_section = {
                    'gitlab': lambda: os.environ['GITLAB_CR_REGISTRY'] + '/',
                    'docker-hub': lambda: 'haumea/'
                    }[registry]()
            task['registry_section'] = registry_section
            template = load_template('templates/docker-build.yml.jinja')
            rendered = template.render(task=task)
            output.append(rendered)

    return '\n'.join(output)

def main():
    pipeline_file = 'pipeline.yml'
    file = load_yaml(pipeline_file)
    steps = generate_steps(file)
    print(steps)

if __name__ == '__main__':
    main()
