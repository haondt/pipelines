from .render_template import load_pipeline_config, get_env, get_public_env, render_template
from .utils import deep_merge
import yaml, argparse

def generate_steps(data, templates: str | None=None):

    tasks = data.get('tasks', [])
    rendered_templates = []
    env = get_env()
    for task_index, task in enumerate(tasks):
        task_env = { k:v for k,v in env.items() }
        task_env['INTERNAL_TASK_INDEX'] = str(task_index)
        task_env['INTERNAL_TASKS_COUNT'] = str(len(tasks))
        rendered_templates.append(render_template(task_env, {}, task, templates=templates))

    allowed_top_level_merge_keys = [
        'stages'
    ]

    loaded_templates = [yaml.safe_load(t) for t in rendered_templates]
    jobs = [k for t in loaded_templates for k in t.keys()]
    counts = {k: jobs.count(k) for k in set(jobs) if k not in allowed_top_level_merge_keys and jobs.count(k) > 1}
    if len(counts) > 0:
        rendered_counts = '\n'.join([f'{k}: {v}' for k, v in counts.items()])
        raise Exception(f'Rendering resulted in one or more jobs with overlapping keys: \n{rendered_counts}')

    merged_output = {}
    for rendered in rendered_templates:
        merged_output = deep_merge(merged_output, yaml.safe_load(rendered))

    return yaml.dump(merged_output)

def main():
    parser = argparse.ArgumentParser(prog='generate')
    parser.add_argument('--templates', help='templates directory')
    parser.add_argument('-f', '--file', help='pipeline file')
    args = parser.parse_args()

    data = load_pipeline_config(args.file)
    steps = generate_steps(data, args.templates)
    public_env = get_public_env()
    for k, v in public_env.items():
        print(f'# {k}: {v}')

    print(steps)

if __name__ == '__main__':
    main()
