from .models import *
from .volume import create_volume_manifest
from .environment import create_environment_manifest
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name
from .service import get_service_name

def create_deployment_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.spec.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)
        component_args = ComponentManifestArguments(
            app_def=args.app_def,
            app_env=args.app_env,
            app_labels=args.app_labels,
            component_labels=component_labels,
            app_annotations=args.app_annotations,
            component_annotations=component_annotations,
            compiled_files_dir=args.compiled_files_dir
        )
        image = component.spec.image
        
        resources_dict = {}
        if component.resources:
            if component.resources.limits:
                resources_dict['limits'] = component.resources.limits.model_dump(exclude_none=True)
            if component.resources.requests:
                resources_dict['requests'] = component.resources.requests.model_dump(exclude_none=True)
        
        container = client.V1Container(
            name=component_name,
            image=image,
            resources=client.V1ResourceRequirements(**resources_dict) if resources_dict else None
        )


        # Create pod template spec
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=component_labels, annotations=component_annotations),
            spec=client.V1PodSpec(containers=[container])
        )
        
        # Create deployment spec
        deployment_spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={
                APP_SELECTOR_NAME: args.app_labels[APP_SELECTOR_NAME],
                COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME]
            }),
            template=pod_template,
        )
        
        # Create deployment
        deployment = client.V1Deployment(
            api_version='apps/v1',
            kind='Deployment',
            metadata=client.V1ObjectMeta(
                name=f"{args.app_def.metadata.name}-{component_name}",
                namespace=args.app_def.metadata.namespace,
                labels=component_labels,
                annotations=component_annotations
            ),
            spec=deployment_spec
        )

        # add volumes
        if component.spec.volumes:
            pod_template_volumes = []

            for volume_spec in component.spec.volumes:
                volume_manifest_name = f"{args.app_def.metadata.name}-{component_name}-{coerce_dns_name(volume_spec.src.human_name())}-{volume_spec.id}"
                volume_map, volume_manifest = create_volume_manifest(component_args, volume_manifest_name, volume_spec)
                manifests.append(volume_manifest)

                pod_template_items = []
                if volume_spec.is_single():
                    assert volume_spec.dest.file is not None # should be true cuz single
                    pod_template_items.append(client.V1KeyToPath(key=volume_map[""], path=os.path.basename(volume_spec.dest.file)))
                else:
                    assert volume_spec.dest.dir is not None # should be true cuz not single
                    for rel_path, map_key in volume_map.items():
                        pod_template_items.append(client.V1KeyToPath(key=map_key, path=rel_path))


                if volume_spec.src.secret:
                    pod_template_volume = client.V1Volume(
                        name=volume_manifest_name,
                        secret=client.V1SecretVolumeSource(
                            secret_name=volume_manifest_name,
                            items=pod_template_items
                        )
                    )
                else:
                    pod_template_volume = client.V1Volume(
                        name=volume_manifest_name,
                        config_map=client.V1ConfigMapVolumeSource(
                            name=volume_manifest_name,
                            items=pod_template_items
                        )
                    )
                pod_template_volumes.append(pod_template_volume)

                if volume_spec.is_single():
                    assert volume_spec.dest.file is not None # should be true cuz single
                    container.volume_mounts = (container.volume_mounts or []) + [client.V1VolumeMount(
                        name=volume_manifest_name,
                        mount_path=volume_spec.dest.file,
                        sub_path=os.path.basename(volume_spec.dest.file),
                        read_only=True
                    )]
                else:
                    container.volume_mounts = (container.volume_mounts or []) + [client.V1VolumeMount(
                        name=volume_manifest_name,
                        mount_path=volume_spec.dest.dir,
                        read_only=True
                    )]

            pod_template.spec.volumes = (pod_template.spec.volumes or []) + pod_template_volumes # type: ignore[no-any-return]
        
        # add env vars
        if component.spec.environment:
            for environment_spec in component.spec.environment:
                environment_manifest_name = f"{args.app_def.metadata.name}-{component_name}-environment-{environment_spec.id}"
                environment_manifest = create_environment_manifest(component_args, environment_manifest_name, environment_spec)
                manifests.append(environment_manifest)

                if container.env_from is None:
                    container.env_from = []

                if environment_spec.secret:
                    container.env_from.append(client.V1EnvFromSource(
                        secret_ref=client.V1SecretEnvSource(
                            name=environment_manifest_name
                        )
                    ))
                else:
                    container.env_from.append(client.V1EnvFromSource(
                        config_map_ref=client.V1ConfigMapEnvSource(
                            name=environment_manifest_name
                        )
                    ))

        # add networking
        if component.spec.networking:
            # add ports
            if component.spec.networking.ports:
                for port_name, port in component.spec.networking.ports.items():
                    port_number = port
                    port_protocol = 'TCP'
                    if isinstance(port, PortConfig):
                        port_number = port.port
                        port_protocol = port.protocol

                    if not container.ports:
                        container.ports = []
                    container.ports.append(client.V1ContainerPort(
                        container_port=port_number,
                        name=port_name,
                        protocol=port_protocol
                    ))

        manifests.append(client.ApiClient().sanitize_for_serialization(deployment))

    return manifests
