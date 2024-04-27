from jinja2_extensions import regex_ismatch

def get_tags(env):
    # tags[tag_source] = tag
    tags = {
            'latest': 'latest'
            }
    if 'CI_COMMIT_TAG' in env:
        if regex_ismatch(env['CI_COMMIT_TAG'], r'^v\d+\.\d+\.\d+$'):
            tags['tag'] = env['CI_COMMIT_TAG'][1:]
    if 'CI_COMMIT_BRANCH' in env:
        tags['commit'] = env['CI_COMMIT_BRANCH'] + '-' + env['CI_COMMIT_SHORT_SHA']
        tags['branch'] = env['CI_COMMIT_BRANCH']
    return tags

def should_use_manual_push(task, tag_source, env):
    auto_push_on = task.get('auto_push_on')
    if auto_push_on is None:
        return True

    source = env['CI_PIPELINE_SOURCE']
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

