import argparse

def main():
    parser = argparse.ArgumentParser(prog='docker-build-kubernetes')
    parser.add_argument('key', help='encryption key')
    parser.add_argument('project', help='project to build')
    args = parser.parse_args()
    build_project(args.project, args.key)

def build_project(project, encryption_key):
    services = filter_services([os.path.join(project, ".haondt.yml")])[project]

    # load base files
    base_env = Environment()
    base_env.load_plugin_yaml_file(os.path.join(project, "env.haondt.yml"), True)
    base_yaml = load_file(os.path.join(project, 'docker-compose-base.haondt.yml'))

    # generate config objects for each service
    service_configs = [build_service_yaml(project, s, base_env, base_yaml) for s in services]
    containers = [c for cfg in service_configs for c in cfg.dict['services'].keys()]

    # merge service configs
    service_config = service_configs[0].dict.copy()
    for cfg in service_configs[1:]:
        service_config = deep_merge(service_config, cfg.dict, conflicts="err")

    # create final file
    final_yaml = yaml.dump(service_config, default_flow_style=False)

    # save
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, 'docker-compose.yml'), 'w') as f:
            f.write(final_yaml)
        with open(os.path.join(td, 'changes.txt'), 'w') as f:
            f.write('\n'.join(containers))

        # copy and hydrate extra service files
        cpy_services(project, td, services)
        for (i, service) in enumerate(services):
            if os.path.isfile(f'{project}/services/{service}/hydrate.haondt.yml'):
                to_hydrate = load_yaml_file(f'{project}/services/{service}/hydrate.haondt.yml')
                for fn in to_hydrate:
                    fn = fn.strip()
                    src = os.path.join(project, 'services', service, fn)
                    dst = os.path.join(td, service, fn)
                    data = load_file(src)
                    hydrated = hydrate_string(data, service_configs[i].env)
                    with open(dst, 'w') as sf:
                        sf.write(hydrated)

            # apply transformations
            transform_file_path = f'{project}/services/{service}/transform.haondt.yml'
            transform_context_path = os.path.join(td, service)
            if os.path.isfile(transform_file_path):
                transformation_config = load_yaml_file(transform_file_path)
                transform = Transformation(transform_context_path, transformation_config, service_configs[i].env)
                transform.perform_transformations()

        tar(td, f'{project}.tar.gz')

        encrypt(encryption_key, os.path.join(td, f'{project}.tar.gz'), f'{project}.enc')

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)

