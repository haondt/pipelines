from .models import *
from typing import Any
from kubernetes import client
from ..utils import coerce_dns_name
from .service import get_service_name

def get_network_policy_name(args: ManifestArguments, component_name: str, host: str, port: str):
    return f"{args.app_def.metadata.name}-{component_name}-rathole-{coerce_dns_name(host)}-{port}"

def create_rathole_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.spec.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)

        networking = component.spec.networking
        if not networking or not networking.rathole_routes:
            continue

        for rathole_route_spec in networking.rathole_routes:
            assert networking.ports is not None
            rathole_route = {
                "apiVersion": "rathole.haondt.dev/v1",
                "kind": "RatholeRoute",
                "metadata": {
                    "name": coerce_dns_name(rathole_route_spec.host),
                    "namespace": args.app_def.metadata.namespace
                },
                "spec": {
                    "virtualHost": rathole_route_spec.host,
                    "service": {
                        "host": f'{get_service_name(args, component_name, rathole_route_spec.port)}.{args.app_def.metadata.namespace}.svc.cluster.local',
                        "port": networking.ports[rathole_route_spec.port]
                    }
                }
            }

            if rathole_route_spec.virtual_path is not None:
                rathole_route['spec']['virtualPath'] = rathole_route_spec.virtual_path
            if rathole_route_spec.virtual_dest is not None:
                rathole_route['spec']['virtualDest'] = rathole_route_spec.virtual_dest
            if rathole_route_spec.max_body_size is not None:
                rathole_route['spec']['maxBodySize'] = rathole_route_spec.max_body_size
            if rathole_route_spec.connection_timeout is not None:
                rathole_route['spec']['connectionTimeout'] = rathole_route_spec.connection_timeout

            manifests.append(rathole_route)

            network_policy = client.V1NetworkPolicy(
                api_version="networking.k8s.io/v1",
                kind="NetworkPolicy",
                metadata=client.V1ObjectMeta(
                    name=get_network_policy_name(args, component_name, rathole_route_spec.host, rathole_route_spec.port),
                    namespace=args.app_def.metadata.namespace,
                    labels=component_labels,
                    annotations=component_annotations
                ),
                spec=client.V1NetworkPolicySpec(
                    pod_selector=client.V1LabelSelector(match_labels={
                        APP_SELECTOR_NAME: component_labels[APP_SELECTOR_NAME],
                        COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME],
                        PROJECT_SELECTOR_NAME: component_labels[PROJECT_SELECTOR_NAME],
                    }),
                    policy_types=["Ingress"],
                    ingress=[
                        client.V1NetworkPolicyIngressRule(
                            _from=[client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(match_labels={
                                    "kubernetes.io/metadata.name": "rathole"
                                })
                            )],
                            ports=[client.V1NetworkPolicyPort(
                                protocol='TCP',
                                port=rathole_route_spec.port
                            )]
                        )
                    ]
                )
            )

            manifests.append(client.ApiClient().sanitize_for_serialization(network_policy))
    return manifests
