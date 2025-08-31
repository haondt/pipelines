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
        existing_services = [k for k,v in body['services'].items() if v['status'] != 'removed']
        modified_services = [k for k,v in body['services'].items() if v['status'] == 'modified']
        removed_services = [k for k,v in body['services'].items() if v['status'] == 'removed']
        is_kubernetes = body['type'] == 'kubernetes'
        redeploy_existing_payload = {
            "services": existing_services,
            "type": body['type'],
            'status': body['status'],
            'removed_services': removed_services
        }
        redeploy_modified_payload = {
            "services": modified_services,
            "type": body['type'],
            'status': body['status'],
            'removed_services': removed_services
        }

        if body['status'] == 'modified':
            if len(existing_services) > 0:
                result[project] = redeploy_existing_payload
            elif is_kubernetes and len(removed_services) > 0:
                result[project] = redeploy_existing_payload
        elif body['status'] == 'unchanged':
            if len(modified_services) > 0:
                result[project] = redeploy_modified_payload
            elif is_kubernetes and len(removed_services) > 0:
                result[project] = redeploy_modified_payload
        elif body['status'] == 'removed':
            if is_kubernetes and len(removed_services) > 0:
                result[project] = redeploy_existing_payload

    return result

def get_project_config(xtra, project):
    if 'project_base_dir' in xtra:
        return load_yaml(os.path.join(xtra['project_base_dir'], project, 'config.haondt.yml'))
    return load_yaml(os.path.join(project, 'config.haondt.yml'))
