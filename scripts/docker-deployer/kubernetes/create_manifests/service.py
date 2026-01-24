from .models import *
from typing import Any
from kubernetes import client

def get_service_name(args: ManifestArguments | ComponentManifestArguments, component_name: str):
    return f"{args.app_def.metadata.name}-{component_name}"

def create_service_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)

        networking = component.networking
        if not networking or not networking.ports:
            continue

        ports: list[client.V1ServicePort] = []
        for port_name, port in networking.ports.items():
            port_protocol = 'TCP'

            if isinstance(port, PortConfig):
                port_protocol = port.protocol
                port_number = port.port
            else:
                port_number = port
            ports.append(client.V1ServicePort(
                protocol=port_protocol,
                port=port_number,
                target_port=port_name,
                name=port_name
            ))

        service = client.V1Service(
            api_version= "v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=get_service_name(args, component_name),
                namespace=args.app_def.metadata.namespace,
                labels=component_labels,
                annotations=component_annotations
            ),
            spec=client.V1ServiceSpec(
                selector={
                    APP_SELECTOR_NAME: component_labels[APP_SELECTOR_NAME],
                    COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME],
                    PROJECT_SELECTOR_NAME: component_labels[PROJECT_SELECTOR_NAME],
                },
                ports=ports
            )
        )

        manifests.append(client.ApiClient().sanitize_for_serialization(service))
    return manifests

