from git import Repo
from gitdb.util import sys
import yaml
import re, os
from lib import dataclasses_tools
from pathlib import Path
from lib.models import ProjectTypeEnum, RepoDiff, ProjectDiff, ServiceDiff, StatusEnum
from git.exc import GitCommandError

def get_file_from_commit(repo: Repo, commit, path: str) -> str | None:
    try:
        return repo.git.show(f"{commit}:{path}")
    except GitCommandError:
        return None

def get_changed_paths(repo_dir: str = "."):
    repo = Repo(repo_dir)
    assert not repo.bare

    commit = repo.head.commit
    previous_commit = commit.parents[0] if commit.parents else None
    if previous_commit:
        diff = commit.diff(previous_commit)
        return [i .a_path for i in diff], previous_commit
    return repo.git.ls_files().splitlines(), None

def get_project_type(repo_dir, project_name) -> ProjectTypeEnum | None:
    base_path = Path(repo_dir)
    config_path = base_path / project_name / "config.haondt.yml"
    if not config_path.is_file():
        return None

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    if "type" not in config:
        return ProjectTypeEnum.DOCKER

    try:
        return ProjectTypeEnum(config["type"])
    except ValueError:
        raise ValueError(
            f"Invalid project type {config['type']!r} in {config_path}. "
            f"Expected one of {[e.value for e in ProjectTypeEnum]}"
        )

def build_repo_map(repo_dir) -> RepoDiff:
    result = RepoDiff()
    base_path = Path(repo_dir)
    for project in base_path.iterdir():
        if not project.is_dir():
            continue

        project_type = get_project_type(repo_dir, project.name)
        if project_type is None:
            continue

        result.projects[project.name] = ProjectDiff(type=project_type)
        services = project/"services"
        if not services.is_dir():
            continue
        for service in services.iterdir():
            if service.is_dir():
                result.projects[project.name].services[service.name] = ServiceDiff()
    return result

def apply_file_changes(repo_dir: str, repo_map: RepoDiff, changed_files, previous_commit) -> RepoDiff:
    base_file_re = r'^[^\/]+\/[^\/]*\.haondt\.yml$'
    bp = re.compile(base_file_re)
    sp = re.compile(r'^[^\/]+\/services\/[^\/]+\/.+$')

    repo = Repo(repo_dir)

    base_files = [f for f in changed_files if bp.match(f)]
    service_files = [f for f in changed_files if sp.match(f)]

    for f in base_files:
        parts = f.split(os.path.sep)
        project = parts[0]

        # project was modified
        if project in repo_map.projects:
            if repo_map.projects[project].status == StatusEnum.UNCHANGED:
                repo_map.projects[project].status = StatusEnum.MODIFIED
        # project was deleted
        else:
            repo_map.projects[project] = ProjectDiff(status=StatusEnum.REMOVED)
            if previous_commit and f.endswith(f"{os.path.sep}config.haondt.yml"):
                old_content = get_file_from_commit(repo, previous_commit, f)
                if old_content:
                    config = yaml.safe_load(old_content) or {}
                    if "type" in config:
                        try:
                            repo_map.projects[project].type = ProjectTypeEnum(config["type"])
                        except ValueError:
                            pass
                    else:
                        repo_map.projects[project].type = ProjectTypeEnum.DOCKER

    for f in service_files:
        parts = f.split(os.path.sep)
        project = parts[0]
        service = parts[2]

        # ensure project exists, shouldn't happen if cicd runs on every commit
        if project not in repo_map.projects:
            repo_map.projects[project] = ProjectDiff(status=StatusEnum.REMOVED)
        elif repo_map.projects[project].status == StatusEnum.UNCHANGED:
            repo_map.projects[project].status = StatusEnum.MODIFIED

        if service in repo_map.projects[project].services:
            if repo_map.projects[project].services[service].status == StatusEnum.UNCHANGED:
                repo_map.projects[project].services[service].status = StatusEnum.MODIFIED
        else:
            repo_map.projects[project].services[service] = ServiceDiff(status=StatusEnum.REMOVED)

    return repo_map

def main():
    if len(sys.argv) > 1:
        repo_path = os.path.realpath(sys.argv[1])
    else:
        repo_path = os.path.realpath(".")
    changed_paths, previous_commit = get_changed_paths(repo_path)

    map = build_repo_map(repo_path)
    map = apply_file_changes(repo_path, map, changed_paths, previous_commit)
    yml = dataclasses_tools.dataclass_to_yaml(map)
    print(yml)

if __name__ == '__main__':
    try:
        main()
    # discard stack trace
    except Exception as e:
        print(f"{type(e).__name__}:", e, file=sys.stderr)
        exit(1)
