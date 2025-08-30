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

