from utils import try_get_version

def get_version(env):
    commit_tag = env.get('CI_COMMIT_TAG')
    if commit_tag is None:
        raise EnvironmentError('not a commit pipeline')
    version = try_get_version(commit_tag)
    if version is None:
        raise ValueError(f'commit tag `{commit_tag}` not in expected format')
    return version
