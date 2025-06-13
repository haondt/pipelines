from utils import try_get_version

def get_tags(env):
    tags = {
            'latest': 'latest'
            }
    commit_tag = env.get('CI_COMMIT_TAG')
    if commit_tag is not None:
        version = try_get_version(commit_tag)
        if version is not None:
            tags['tag'] = version
    if 'CI_COMMIT_BRANCH' in env:
        tags['commit'] = env['CI_COMMIT_BRANCH'] + '-' + env['CI_COMMIT_SHORT_SHA']
        tags['branch'] = env['CI_COMMIT_BRANCH']
    return tags

def get_version(env):
    commit_tag = env.get('CI_COMMIT_TAG')
    if commit_tag is not None:
        return commit_tag
    if 'CI_COMMIT_BRANCH' in env:
        return env['CI_COMMIT_BRANCH'] + '-' + env['CI_COMMIT_SHORT_SHA']
    return None

def should_use_manual_push(task, tag_source, env):
    auto_push_on = task.get('auto')
    if auto_push_on is None:
        return True

    source = env['ROOT_PIPELINE_SOURCE']
    has_tag = 'CI_COMMIT_TAG' in env
    branch = env.get('CI_COMMIT_BRANCH')

    def check_entry(entry):
        nonlocal source
        nonlocal has_tag
        nonlocal branch
        if 'source' in entry:
            if entry['source'] != source:
                return False
        if 'has_tag' in entry:
            if bool(entry['has_tag']) != has_tag:
                return False
        if 'branch' in entry:
            if entry['branch'] != branch:
                return False
        if 'tag_source' in entry:
            if entry['tag_source'] != tag_source:
                return False
        return True

    for entry in auto_push_on:
        if check_entry(entry):
            return False
    return True

def is_gitlab_hosted_runner(env):
    return env.get('CI_RUNNER_HOSTING_TYPE') == 'gitlab'
