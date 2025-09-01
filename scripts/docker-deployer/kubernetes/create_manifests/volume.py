
from .models import ComponentManifestArguments
from ..models import *
from ..utils import make_config_map_key
from typing import Any
import os, glob
from kubernetes import client

def load_volume_source_data(args: ComponentManifestArguments, volume: VolumeSource) -> dict[str, str]:
    if volume.glob:
        results = {}
        for file_path in glob.glob(os.path.join(args.compiled_files_dir, volume.glob)):
            if os.path.isdir(file_path):
                continue
            with open(file_path, 'r') as f:
                data = f.read()
            rel_path = os.path.relpath(file_path, args.compiled_files_dir)
            results[rel_path] = data
        return results
    elif volume.dir:
        results = {}
        full_path = os.path.join(args.compiled_files_dir, volume.dir)
        for root, _, files in os.walk(full_path):
            for name in files:
                file_path = os.path.join(root, name)
                rel_path = os.path.relpath(file_path, args.compiled_files_dir)
                # drop the parent folder, since that is determined by the volume mount
                rel_path = os.sep.join(rel_path.split(os.path.sep)[1:])
                with open(file_path, 'r') as f:
                    results[rel_path] = f.read()
        return results
    elif volume.file:
        results = {}
        full_path = os.path.join(args.compiled_files_dir, volume.file)
        with open(full_path, 'r') as f:
            return { "": f.read() }
    elif volume.data:
        return { "": volume.data }
    else:
        raise ValueError(f'Unsupported volume type {volume}')

    
def create_volume_manifest(args: ComponentManifestArguments, volume_manifest_name: str, volume_spec: VolumeSpec) -> tuple[dict[str, str], dict[str, Any]]:
    """ returns a tuple of a dict with relative path -> keys, and the manifest body"""

    source_data = load_volume_source_data(args, volume_spec.src)
    if volume_spec.is_single():
        map_data = { "data" : source_data[""] }
        map_map = { "": "data" }
    else:
        map_data = {}
        map_map = {}
        for k,v in source_data.items():
            key = make_config_map_key(k)
            map_data[key] = source_data[k]
            map_map[k] = key

    
    if volume_spec.src.secret:
        map = client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="Opaque",
            metadata=client.V1ObjectMeta(
                name=volume_manifest_name,
                namespace=args.app_def.metadata.namespace,
                labels=args.component_labels,
                annotations=args.component_annotations,
            ),
            string_data=map_data
        )
    else:
        map = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(
                name=volume_manifest_name,
                namespace=args.app_def.metadata.namespace,
                labels=args.component_labels,
                annotations=args.component_annotations,
            ),
            data=map_data
        )

    return map_map, client.ApiClient().sanitize_for_serialization(map)
