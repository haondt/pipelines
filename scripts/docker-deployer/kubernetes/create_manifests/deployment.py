from pydantic_core.core_schema import none_schema
from .models import *
from .volume import create_volume_manifest
from .environment import create_environment_manifest
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name, generate_stable_id
from .service import get_service_name
from .startup import create_startup_init_containers
from .charon import create_charon_component_manifests
from .gluetun import create_gluetun_component_manifests
from .observability import create_observability_manifests

def create_deployment_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)
        component_args = ComponentManifestArguments(
            app_def=args.app_def,
            app_env=args.app_env,
            app_labels=args.app_labels,
            component_labels=component_labels,
            app_annotations=args.app_annotations,
            component_annotations=component_annotations,
            compiled_files_dir=args.compiled_files_dir,
            component_name=component_name
        )
        image = component.image
        
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

            

        if component.command:
            container.command = component.command
        if component.args:
            container.args = component.args

        # Create pod template spec
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=component_labels, annotations=component_annotations),
            spec=client.V1PodSpec(containers=[container]),
        )
        assert pod_template.spec is not None
        
        # Create deployment spec
        deployment_spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={
                APP_SELECTOR_NAME: args.app_labels[APP_SELECTOR_NAME],
                COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME]
            }),
            template=pod_template,
            strategy=client.V1DeploymentStrategy(
                type='Recreate'
            )
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

        if component.resources and component.resources.gpu.enabled:
            if component.resources.gpu.use_limit:
                if container.resources is None:
                    container.resources = client.V1ResourceRequirements()
                if container.resources.limits is None:
                    container.resources.limits = {}
                container.resources.limits[component.resources.gpu.resource_name] = 1

            pod_template.spec.runtime_class_name = component.resources.gpu.runtime_class_name


        # add volumes
        if component.volumes:
            pod_template_volumes = []

            for volume_id, volume_spec in component.volumes.items():
                volume_manifest_name = volume_id

                volume_manifests, pod_volumes, pod_volume_mounts = create_volume_manifest(component_args, volume_manifest_name, volume_spec)

                manifests += volume_manifests
                pod_template_volumes += pod_volumes
                if container.volume_mounts is None:
                    container.volume_mounts = []
                container.volume_mounts += pod_volume_mounts

            assert pod_template.spec is not None
            if pod_template.spec.volumes is None:
                pod_template.spec.volumes = []
            pod_template.spec.volumes += pod_template_volumes
        
        # add env vars
        if component.environment:
            for i, environment_spec in enumerate(component.environment):
                environment_manifest_name = f"{args.app_def.metadata.name}-{component_name}-environment-{i}"
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
        if component.networking:

            # add ports
            if component.networking.ports:
                for port_name, port in component.networking.ports.items():
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

        # add security
        if component.security:
            security = component.security
            def add_security_context(c):
                if c.security_context is None:
                    c.security_context = client.V1SecurityContext()

            # add capabilities
            if security.cap and security.cap.add:
                add_security_context(container)
                assert container.security_context is not None
                if container.security_context.capabilities is None:
                    container.security_context.capabilities = client.V1Capabilities()
                if container.security_context.capabilities.add is None:
                    container.security_context.capabilities.add = []
                container.security_context.capabilities.add += security.cap.add
            if security.sysctls:
                pod_template.spec.security_context = pod_template.spec.security_context or client.V1PodSecurityContext(sysctls=[])
                for sysctl in security.sysctls:
                    assert pod_template.spec.security_context.sysctls is not None
                    pod_template.spec.security_context.sysctls.append(client.V1Sysctl(
                        name=sysctl,
                        value="1"
                    ))
            if security.user:
                add_security_context(container)
                assert container.security_context is not None
                container.security_context.run_as_user = security.user
            if security.group:
                add_security_context(container)
                assert container.security_context is not None
                container.security_context.run_as_group = security.group


            if security.groups:
                if pod_template.spec.security_context is None:
                    pod_template.spec.security_context = client.V1PodSecurityContext()
                if pod_template.spec.security_context.supplemental_groups is None:
                    pod_template.spec.security_context.supplemental_groups = []
                pod_template.spec.security_context.supplemental_groups += security.groups.add # type: ignore

        # add startup
        if component.startup:

            # add init containers
            if component.startup.tasks:
                init_containers = create_startup_init_containers(component_args, component.startup.tasks, container.volume_mounts)
                if len(init_containers) > 0:
                    if pod_template.spec.init_containers is None:
                        pod_template.spec.init_containers = []
                    pod_template.spec.init_containers += init_containers

        if component.charon:
            manifests += create_charon_component_manifests(component_args, component.charon, deployment, pod_template.spec.volumes)

        if component.gluetun:
            manifests += create_gluetun_component_manifests(component_args, component.gluetun, deployment)

        if component.observability:
            manifests += create_observability_manifests(component_args, component.observability)

        manifests.append(client.ApiClient().sanitize_for_serialization(deployment))

    return manifests
