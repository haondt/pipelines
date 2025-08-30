import yaml
import os

def should_use_manual_deploy(task, env):
    auto_push_on = task.get('auto')
    if auto_push_on is None:
        return True

    source = env['ROOT_PIPELINE_SOURCE']
    branch = env.get('CI_COMMIT_BRANCH')

    def check_entry(entry):
        nonlocal source
        nonlocal branch
        if 'source' in entry:
            if entry['source'] != source:
                return False
        if 'branch' in entry:
            if entry['branch'] != branch:
                return False
        return True

    for entry in auto_push_on:
        if check_entry(entry):
            return False
    return True

def load_yaml(fn):
    with open(fn, 'r') as f:
        return yaml.safe_load(f)

def get_projects(xtra):
    data = load_yaml(xtra['changed_services_file'])
    result = {}
    for project, body in data['projects'].items():
        if body['status'] == 'modified':
            result[project] = [k for k,v in body['services'].items() if v['status'] != 'removed']
        # ignore removed.. TODO
        elif body['status'] == 'unchanged':
            # also ignoring removed...
            result[project] = [k for k,v in body['services'].items() if v['status'] == 'modified']
    return result

def get_project_config(xtra, project):
    if 'project_base_dir' in xtra:
        return load_yaml(os.path.join(xtra['project_base_dir'], project, 'config.haondt.yml'))
    return load_yaml(os.path.join(project, 'config.haondt.yml'))
