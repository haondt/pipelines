from render_template import load_pipeline_config, get_env, get_public_env, render_template, deduplicate_keys

def generate_steps(data):
    tasks = data.get('tasks', [])
    env = get_env()
    output = [render_template(env, task) for task in tasks]
    return '\n'.join(output)


def main():
    data = load_pipeline_config()
    steps = generate_steps(data)
    dd_steps = deduplicate_keys(steps)

    public_env = get_public_env()
    for k, v in public_env.items():
        print(f'# {k}: {v}')

    print(dd_steps)

if __name__ == '__main__':
    main()
