from .models import *
from .volume import create_volume_manifest
from .environment import create_environment_manifest
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name
from .service import get_service_name

def create_network_policy_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)
        
        # add network dependencies
        if not component.networking or not component.networking.dependencies:
            continue

        component_selector = client.V1NetworkPolicyPeer(
            pod_selector=client.V1LabelSelector(match_labels={
                APP_SELECTOR_NAME: args.app_labels[APP_SELECTOR_NAME],
                COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME]
            }),
            namespace_selector=client.V1LabelSelector(match_labels={
                NAMESPACE_SELECTOR_NAME: args.app_def.metadata.namespace
            })
        )

        for net_dep in component.networking.dependencies:
            dep_namespace = args.app_def.metadata.namespace
            dep_app = args.app_def.metadata.name
            dep_component = net_dep.name
            dep_port = net_dep.port
            dep_protocol = net_dep.protocol

            parts = net_dep.name.split('/')
            if len(parts) > 1:
                dep_component = parts[-1]
                dep_app = parts[-2]
            if len(parts) > 2:
                dep_namespace = parts[-3]
            if len(parts) > 3:
                raise ValueError(f"Unexpected number of parts: {parts}") 


            network_policy = client.V1NetworkPolicy(
                api_version="networking.k8s.io/v1",
                kind="NetworkPolicy",
                metadata=client.V1ObjectMeta(
                    name=f"{args.app_def.metadata.name}-{component_name}-{net_dep.id}",
                    namespace=dep_namespace,
                    labels=component_labels,
                    annotations=component_annotations
                ),
                spec=client.V1NetworkPolicySpec(
                    pod_selector=client.V1LabelSelector(match_labels={
                        APP_SELECTOR_NAME: dep_app,
                        COMPONENT_SELECTOR_NAME: dep_component
                    }),
                    policy_types=["Ingress"],
                    ingress=[
                        client.V1NetworkPolicyIngressRule(
                            _from=[component_selector],
                            ports=[client.V1NetworkPolicyPort(
                                protocol=dep_protocol,
                                port=dep_port
                            )]
                        )
                    ]
                )
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(network_policy))

    return manifests
