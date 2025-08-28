import yaml, argparse, os, sys

def get_containers(project, service) -> list[str]:
    path = os.path.join(project, 'services', service, 'docker-compose.yml') 
    if not os.path.isfile(path):
        raise ValueError(f"no such file: {path}")
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return list(data['services'].keys())

def main():
    parser = argparse.ArgumentParser(prog='docker-build')
    parser.add_argument('project', help='services to get containers from')
    args = parser.parse_args()
    services = yaml.safe_load(sys.stdin.read())[args.project]
    containers = [c for s in services for c in get_containers(args.project, s)]
    print('\n'.join(containers))

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)
