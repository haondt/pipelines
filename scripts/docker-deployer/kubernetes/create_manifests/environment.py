from .models import ComponentManifestArguments
from ..models import *
from ..utils import make_config_map_key
from typing import Any
import os, glob
from dotenv import dotenv_values
from kubernetes import client

def load_environment_source_data(args: ComponentManifestArguments, env: EnvironmentSpec) -> dict[str, str]:
    if env.raw is not None:
        return { k: str(v) for k,v in env.raw.items() }
    elif env.file is not None:
        full_path = os.path.join(args.compiled_files_dir, env.file)
        values = dotenv_values(full_path)
        return { k: v or "" for k, v in values.items()}
    else:
        raise ValueError(f'Unsupported environment type {env}')


def create_environment_manifest(args: ComponentManifestArguments, environment_manifest_name: str, environment_spec: EnvironmentSpec) -> dict[str, Any]:

    source_data = load_environment_source_data(args, environment_spec)
    
    if environment_spec.secret:
        map = client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="Opaque",
            metadata=client.V1ObjectMeta(
                name=environment_manifest_name,
                namespace=args.app_def.metadata.namespace,
                labels=args.component_labels,
                annotations=args.component_annotations,
            ),
            string_data=source_data
        )
    else:
        map = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(
                name=environment_manifest_name,
                namespace=args.app_def.metadata.namespace,
                labels=args.component_labels,
                annotations=args.component_annotations,
            ),
            data=source_data
        )

    return client.ApiClient().sanitize_for_serialization(map)
