import os
import functools
from gitdb.util import sys
import requests
import json
from .yaml_tools import load_file


@functools.cache
def get_env(key):
    if key not in os.environ:
        raise KeyError(f"no such environment variable: {key}")
    return os.environ[key]

def try_get_env(key, default: str | None = None) -> str | None:
    if key not in os.environ:
        return default
    return os.environ[key]


# execute a plugin
def execute_plugin(name, args) -> str:
    if name == 'secret':
        if len(args) != 2:
            print(f"Unexpected number of arguments for plugin \'secret\': {args}", file=sys.stderr)
        return infisical(args[1], args[0])
    if name == 'gsm':
        if len(args) < 1:
            print(f"Unexpected number of arguments for plugin \'gsm\': {args}", file=sys.stderr)
        return gsm(args[0], args[1:])
    if name == 'env':
        if len(args) != 1:
            print(f"Unexpected number of arguments for plugin \'env\': {args}", file=sys.stderr)
        return env(args[0])
    if name == 'yaml':
        if len(args) < 1:
            print(f"Unexpected number of arguments for plugin \'yaml\': {args}", file=sys.stderr)
        return yaml(args[0], args[1:])
    if name == 'http':
        if len(args) < 1:
            print(f"Unexpected number of arguments for plugin \'http\': {args}", file=sys.stderr)
        return http_plugin(args[0], *args[1:])
    raise ValueError(f"Unkown plugin: {name}")

# secret('path/to/my/secret', 'my-secret')
def infisical(secret_name, secret_path) -> str:
    key = get_env('INFISICAL_SECRET_KEY')
    url = get_env('INFISICAL_URL')
    workspace_id = get_env('INFISICAL_WORKSPACE_ID')

    secret_url = f"{url}/api/v3/secrets/raw/{secret_name}?environment=prod&workspaceId={workspace_id}&secretPath=/{secret_path}/"
    try:
        response = requests.get(secret_url, headers={"Authorization": f"Bearer {key}"}, timeout=1)
        if response.status_code != 200:
            raise RuntimeError(f'unexpected status: {response.status_code}')
        return f"{response.json()['secret']['secretValue']}"
    except:
        raise ValueError(f"Unable to retrieve secret {secret_path}/{secret_name}")

# http('config-name', 'url=https://www.example.com', 'headers={"Authorization": "Bearer some-token"}')
# http('config-name') -> will use HTTP_CONFIG-NAME_URL or HTTP_CONFIG_NAME_BASEURL
def http_plugin(config_name, *args) -> str:
    try:
        key_prefix = f'HTTP_{config_name.upper()}_'
        config_args = { arg.split("=", 1)[0]: arg.split("=", 1)[1] for arg in args }

        url = config_args.get("url", try_get_env(f"{key_prefix}URL"))

        if url is None:
            baseurl = config_args.get("baseurl", get_env(f"{key_prefix}BASEURL")).rstrip('/')
            path = config_args.get("path", try_get_env(f"{key_prefix}PATH", "")).lstrip('/')
            url = f'{baseurl}/{path}'
        method = config_args.get("method", try_get_env(f"{key_prefix}METHOD", "GET")).upper()
        body = config_args.get("body", try_get_env(f"{key_prefix}BODY", None))
        headers = config_args.get("headers", try_get_env(f"{key_prefix}HEADERS", None))
        headers = json.loads(headers) if headers is not None else None
        query = config_args.get("query", try_get_env(f"{key_prefix}QUERY", None))
        query = json.loads(query) if query is not None else None

        timeout = config_args.get("timeout", try_get_env(f"{key_prefix}TIMEOUT", "1"))
        timeout = int(timeout)

        response = requests.request(method, url, headers=headers, params=query, json=body, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f'unexpected status: {response.status_code}')
        return response.text
    except:
        plugin_params = ', '.join([f"'{i}'" for i in [config_name] + [*args]])
        raise ValueError(f"Unable to execute plugin http({plugin_params})")


# gsm('my-secret-name', 'tag1', 'tag2', ...)
def gsm(secret_name, secret_tags) -> str:
    key = get_env('GSM_API_KEY')
    url = get_env('GSM_URL')

    original_plugin = lambda: f'gsm(\'{secret_name}\', ' + ', '.join([f"'{i}'" for i in  secret_tags]) + ')'
    secret_url = f"{url}/api/secrets"
    try:
        response = requests.get(secret_url, 
            headers={"Authorization": f"Bearer {key}"},
            timeout=1,
            params={
                'name': secret_name,
                'tags': secret_tags
            })
        if response.status_code != 200:
            raise RuntimeError(f'unexpected status: {response.status_code}')
        response_json = response.json()
        if len(response_json) != 1:
            raise RuntimeError(f'expected one secret, but received {len(response_json)} for plugin {original_plugin()}')
        return response_json[0]['value']
    except:
        raise ValueError(f"Unable to execute plugin {original_plugin()}")

# env('MY_ENV_VAR'), referring to the system environment. this does not recurse.
def env(variable_name) -> str:
    return get_env(variable_name)

# ENVIRONMENT_VARIABLE should be a file path
# yaml('ENVIRONMENT_VARIABLE', 'foo', 0, 'bar', 'baz')
# if ENVIRONMENT_VARIABLE is not set, then interpret input as a file path 
# yaml('path/to/my/yaml.yml', 'foo', 0, 'bar', 'baz')
def yaml(file_path,  yaml_path):
    original_plugin = lambda: f'yaml(\'{file_path}\', ' + ', '.join([f"'{i}'" if isinstance(i, str) else f'{i}' for i in  yaml_path]) + ')'
    if file_path in os.environ:
        file_path = get_env(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    try:
        current = load_file(file_path)
        for key in yaml_path:
            if isinstance(key, int) or isinstance(key, str):
                current = current[key]
        if not isinstance(current, str):
            raise RuntimeError(f'yaml path did not end in a string: {original_plugin()}')
        return current
    except:
        raise ValueError(f"Unable to execute plugin {original_plugin()}")
