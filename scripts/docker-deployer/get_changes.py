from git import Repo
from gitdb.util import sys
import yaml
import re, os

def get_changed_paths():
    repo = Repo(".")
    assert not repo.bare

    commit = repo.head.commit
    previous_commit = commit.parents[0] if commit.parents else None
    if previous_commit:
        diff = commit.diff(previous_commit)
        return [i .a_path for i in diff]
    return repo.git.ls_files().splitlines()

# if any of the files are a base (*.haondt.yml) file, then return all the service directories
def filter_services(files):
    base_file_re = r'^[^\/]+\/[^\/]*\.haondt\.yml$'
    bp = re.compile(base_file_re)
    sp = re.compile(r'^[^\/]+\/services\/[^\/]+\/.+$')

    services: dict[str, set[str]] = {}
    projects: set = set()
    for f in files:
        base_match = bool(bp.match(f))
        service_match = sp.match(f)
        if (not base_match) and (not service_match):
            continue

        parts = f.split(os.path.sep)
        project = parts[0]
        if base_match:
            projects.add(project)
            continue
        elif project in projects:
            continue

        if project not in services:
            services[project] = set()
        services[project].add(parts[2])
    for project in projects:

        # skip deleted projects
        if not os.path.isdir(project):
            continue
        all_services = [d for d in next(os.walk(os.path.join(project, 'services')))[1] if os.path.isfile(os.path.join(project, 'services', d, 'docker-compose.yml'))]
        services[project] = set(all_services)

    return { k: list(v) for k, v in services.items() }

def main():
    changes = get_changed_paths()
    changed_services = filter_services(changes)
    if len(changed_services) == 0:
        return
    yml = yaml.dump(changed_services, default_flow_style=False)
    print(yml)

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)
