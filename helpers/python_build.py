from utils import try_get_version

def get_version(env):
    commit_tag = env.get('CI_COMMIT_TAG')
    if commit_tag is None:
        raise RuntimeError('not a commit pipeline')
    version = try_get_version(commit_tag)
    if version is None:
        raise ValueError(f'commit tag `{commit_tag}` not in expected format')
    return version

def should_use_manual_push(task, env):
    auto_push_on = task.get('auto')
    if auto_push_on is None:
        return True

    source = env['CI_PIPELINE_SOURCE']
    for entry in auto_push_on:
        if 'source' not in entry:
            continue
        if entry['source'] == source:
            return False

    return True

