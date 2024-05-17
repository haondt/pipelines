from render_template import load_pipeline_config, get_env, get_public_env, render_template, deduplicate_keys
from utils import deep_merge
import yaml

def generate_steps(data):
    tasks = data.get('tasks', [])
    env = get_env()
    rendered_templates = [render_template(env, task) for task in tasks]
    merged_output = {}
    for rendered in rendered_templates:
        merged_output = deep_merge(merged_output, yaml.safe_load(rendered))

    return yaml.dump(merged_output)

def main():
    data = load_pipeline_config()
    steps = generate_steps(data)
    public_env = get_public_env()
    for k, v in public_env.items():
        print(f'# {k}: {v}')

    print(steps)

if __name__ == '__main__':
    main()
