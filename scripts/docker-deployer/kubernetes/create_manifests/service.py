from sys import api_version
from .models import *
from .volume import create_volume_manifest
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name

def create_service_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.spec.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)

        networking = component.spec.networking
        if not networking or not networking.ports:
            continue

        for port_name, port in networking.ports.items():
            port_protocol = 'TCP'
            port_number = port

            if isinstance(port, PortConfig):
                port_protocol = port.protocol
                port_number = port.port

            service = client.V1Service(
                api_version= "v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=f"{args.app_def.metadata.name}-{component_name}-{port_name}-service",
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
                    ports=[client.V1ServicePort(
                        protocol=port_protocol,
                        port=port_number,
                        target_port=port_name,
                        name=port_name
                    )]
                )
            )

            manifests.append(client.ApiClient().sanitize_for_serialization(service))
    return manifests

