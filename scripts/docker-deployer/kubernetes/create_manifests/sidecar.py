from .models import APP_SELECTOR_NAME, PROJECT_SELECTOR_NAME, COMPONENT_SELECTOR_NAME, ComponentManifestArguments
from ..models import *
from ..utils import coerce_dns_name, make_config_map_key
from ...lib.render_template import render_template
from typing import Any
from kubernetes import client
from .volume import create_volume_manifest
from .service import get_service_name
from .environment import create_environment_manifest

def create_sidecar_manifests(args: ComponentManifestArguments, sidecars: dict[str, SidecarConfig]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[client.V1Container]]:
    manifests = []
    pod_template_volumes = []
    sidecar_containers = []
    for sidecar_name, sidecar_config in sidecars.items():
        sidecar_container = client.V1Container(
            name=sidecar_name,
            image=sidecar_config.image,
        )

        if sidecar_config.command:
            sidecar_container.command = sidecar_config.command
        if sidecar_config.args:
            sidecar_container.args = sidecar_config.args

        if sidecar_config.volumes:
            for volume_id, volume_spec in sidecar_config.volumes.items():
                volume_manifests, pod_volumes, volume_mounts = create_volume_manifest(args, volume_id, volume_spec)

                manifests += volume_manifests
                pod_template_volumes += pod_volumes
                if sidecar_container.volume_mounts is None:
                    sidecar_container.volume_mounts = []
                sidecar_container.volume_mounts += volume_mounts

        if sidecar_config.environment:
            for i, environment_spec in enumerate(sidecar_config.environment):
                environment_manifest_name = f"{args.app_def.metadata.name}-{args.component_name}-{sidecar_name}-environment-{i}"
                environment_manifest = create_environment_manifest(args, environment_manifest_name, environment_spec)
                manifests.append(environment_manifest)

                if sidecar_container.env_from is None:
                    sidecar_container.env_from = []

                if environment_spec.secret:
                    sidecar_container.env_from.append(client.V1EnvFromSource(
                        secret_ref=client.V1SecretEnvSource(
                            name=environment_manifest_name
                        )
                    ))
                else:
                    sidecar_container.env_from.append(client.V1EnvFromSource(
                        config_map_ref=client.V1ConfigMapEnvSource(
                            name=environment_manifest_name
                        )
                    ))
        sidecar_containers.append(sidecar_container)


    return manifests, pod_template_volumes, sidecar_containers
    
