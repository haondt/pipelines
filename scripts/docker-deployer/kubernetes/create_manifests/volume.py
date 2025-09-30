from .models import ComponentManifestArguments
from ..models import *
from ..utils import make_config_map_key
from typing import Any
import os, glob
from kubernetes import client

def load_volume_single_data(args: ComponentManifestArguments, volume: VolumeSource) -> str:
    if volume.file:
        full_path = os.path.join(args.compiled_files_dir, volume.file)
        with open(full_path, 'r') as f:
            return f.read()
    elif volume.data:
        return volume.data
    else:
        raise ValueError(f'Unsupported volume type {volume}')

def load_volume_map_data(args: ComponentManifestArguments, volume: VolumeSource) -> dict[str, str]:
    """load the data as a dictionary of {relative path: data}"""
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
    else:
        raise ValueError(f'Unsupported volume type {volume}')

def create_pvc_manifest(args: ComponentManifestArguments, volume_manifest_name: str, pvc: PVCVolumeSource) -> client.V1PersistentVolumeClaim:
    storage_class = None
    if pvc.storage_class:
        storage_class = pvc.storage_class
    elif args.app_def.defaults.pvc is not None \
        and args.app_def.defaults.pvc.storage_class is not None:
        storage_class = args.app_def.defaults.pvc.storage_class
    else:
        raise ValueError(f'Missing pvc storage class {pvc}')

    storage_size = None
    if pvc.size:
        storage_size = pvc.size
    elif args.app_def.defaults.pvc is not None \
        and args.app_def.defaults.pvc.size is not None:
        storage_size = args.app_def.defaults.pvc.size
    else:
        raise ValueError(f'Missing pvc storage size {pvc}')

    return client.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=client.V1ObjectMeta(
            name=volume_manifest_name,
            namespace=args.app_def.metadata.namespace,
            labels=args.component_labels,
            annotations=args.component_annotations,
        ),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            storage_class_name=storage_class,
            resources=client.V1VolumeResourceRequirements(
                requests={ "storage": storage_size }
            )
        )
    )
    
def create_volume_manifest(args: ComponentManifestArguments, volume_manifest_name: str, volume_spec: VolumeSpec) -> tuple[list[dict[str, Any]], list[client.V1Volume], list[client.V1VolumeMount]]:
    """ returns a tuple of manifests, volumes and volume mounts"""

    manifests: list[Any] = []
    volumes: list[client.V1Volume] = []
    volume_mounts: list[client.V1VolumeMount] = []
    
    if volume_spec.src.host_dir:
        volumes.append(client.V1Volume(
            name=volume_manifest_name,
            host_path=client.V1HostPathVolumeSource(
                path=volume_spec.src.host_dir,
                type='Directory'
            )
        ))
        volume_mounts.append(client.V1VolumeMount(
            name=volume_manifest_name,
            mount_path=volume_spec.dest.dir,
            read_only=True
        ))

    elif volume_spec.src.pvc:
        map = create_pvc_manifest(args, volume_manifest_name, volume_spec.src.pvc)
        manifests.append(client.ApiClient().sanitize_for_serialization(map))

        volumes.append(client.V1Volume(
            name=volume_manifest_name,
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name=volume_manifest_name
            )
        ))
        volume_mounts.append(client.V1VolumeMount(
            name=volume_manifest_name,
            mount_path=volume_spec.dest.dir,
        ))

    elif volume_spec.src.scratch:
        volumes.append(client.V1Volume(
            name=volume_manifest_name,
            empty_dir=client.V1EmptyDirVolumeSource(
                size_limit=volume_spec.src.scratch.size
            )
        ))
        volume_mounts.append(client.V1VolumeMount(
            name=volume_manifest_name,
            mount_path=volume_spec.dest.dir,
        ))

    elif volume_spec.src.tmpfs:
        volumes.append(client.V1Volume(
            name=volume_manifest_name,
            empty_dir=client.V1EmptyDirVolumeSource(
                size_limit=volume_spec.src.tmpfs.size,
                medium='Memory'
            )
        ))
        volume_mounts.append(client.V1VolumeMount(
            name=volume_manifest_name,
            mount_path=volume_spec.dest.dir,
        ))


    else:
        pod_template_items = []
        if volume_spec.is_single():
            assert volume_spec.dest.file is not None # should be true cuz single
            source_data = load_volume_single_data(args, volume_spec.src)
            map_data = { "data": source_data }
            pod_template_items.append(client.V1KeyToPath(key="data", path=os.path.basename(volume_spec.dest.file)))
            volume_mounts.append(client.V1VolumeMount(
                name=volume_manifest_name,
                mount_path=volume_spec.dest.file,
                sub_path=os.path.basename(volume_spec.dest.file),
                read_only=True
            ))
        else:
            assert volume_spec.dest.dir is not None # should be true cuz not single
            source_data = load_volume_map_data(args, volume_spec.src)
            map_data = {}
            for rel_path, data in source_data.items():
                map_key = make_config_map_key(rel_path)
                map_data[map_key] = data
                pod_template_items.append(client.V1KeyToPath(key=map_key, path=rel_path))

            volume_mounts.append(client.V1VolumeMount(
                name=volume_manifest_name,
                mount_path=volume_spec.dest.dir,
                read_only=True
            ))

        if volume_spec.src.secret:
            volumes.append(client.V1Volume(
                name=volume_manifest_name,
                secret=client.V1SecretVolumeSource(
                    secret_name=volume_manifest_name,
                    items=pod_template_items
                )
            ))
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
            manifests.append(client.ApiClient().sanitize_for_serialization(map))
        else:
            volumes.append(client.V1Volume(
                name=volume_manifest_name,
                config_map=client.V1ConfigMapVolumeSource(
                    name=volume_manifest_name,
                    items=pod_template_items
                )
            ))
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
            manifests.append(client.ApiClient().sanitize_for_serialization(map))

    return manifests, volumes, volume_mounts
