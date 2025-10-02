import yaml, argparse, os
from pathlib import Path

def get_services(project_path) -> list[str]:
    base_path = Path(project_path)
    services = base_path/"services"
    service_list = []
    if not services.is_dir():
        return []
    for service in services.iterdir():
        if service.is_dir() and os.path.isfile(service/"docker-compose.yml"):
            service_list.append(service.parts[-1])
    return service_list

def get_docker_services(project_path, service):
    docker_compose_file_path = Path(project_path)/service/'docker-compose.yml'
    l = []
    if os.path.isfile(docker_compose_file_path):
        with open(docker_compose_file_path) as f:
            data = yaml.safe_load(f)
            if 'services' in data:
                for k in data['services'].keys():
                    l.append(k)
    return l


def main():
    parser = argparse.ArgumentParser(prog='get-containers')
    parser.add_argument('changes', help='repository map')
    parser.add_argument('project', help='services to get containers from')
    parser.add_argument('rendered_project_directory', help='directory to search for the rendered project files, to pull docker container lists from')
    args = parser.parse_args()

    with open(args.changes) as f:
        data = yaml.safe_load(f)

    if args.project not in data['projects']:
        return

    services = set(get_services(args.project))
    for k, v in data['projects'][args.project]['services'].items():
        if v['status'] == 'removed' and k in services:
            services.remove(k)

    if data['projects'][args.project]['status'] != 'modified':
        for k, v in data['projects'][args.project]['services'].items():
            if v['status'] != 'modified' and k in services:
                services.remove(k)

    docker_services = []
    for service in services:
        docker_services += get_docker_services(args.rendered_project_directory, service)


    print(' '.join(docker_services))

if __name__ == '__main__':
    main()
