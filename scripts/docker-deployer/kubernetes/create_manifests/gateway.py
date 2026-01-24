from .models import *
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name, hash_str
from .service import get_service_name
from ..crds import gateway_api

def get_http_route_name(args: ManifestArguments, component_name: str, host: str):
    return f"{component_name}-{coerce_dns_name(host)}"

def get_network_policy_name(args: ManifestArguments, component_name: str):
    return f"{args.app_def.metadata.name}-{component_name}-gateway"

def create_gateway_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.components.items():
        component_labels = args.component_labels_factory(component)

        networking = component.networking
        if not networking or not networking.gateway or len(networking.gateway.http_routes) == 0:
            continue

        policy_ports = set()

        for http_route_spec in networking.gateway.http_routes:

            first_host = http_route_spec.host
            if first_host is None:
                if http_route_spec.hosts is not None and len(http_route_spec.hosts) > 0:
                    first_host = http_route_spec.hosts[0]
                else:
                    first_host = ''

            hostnames = []
            if http_route_spec.host is not None:
                hostnames.append(http_route_spec.host)
            hostnames += http_route_spec.hosts or []

            http_route = gateway_api.HttpRoute(
                metadata=client.V1ObjectMeta(
                    name=get_http_route_name(args, component_name, first_host),
                    namespace=args.app_def.metadata.namespace,
                    labels=args.app_labels.copy(),
                    annotations=args.app_annotations.copy()
                ),
                spec=gateway_api.HttpRouteSpec(
                    parent_refs=[gateway_api.ParentReference(
                        name=args.app_def.defaults.networking.gateway.name,
                        namespace=args.app_def.defaults.networking.gateway.namespace
                    )],
                    hostnames=hostnames,
                    rules=[gateway_api.HttpRouteRule(
                        backend_refs=[gateway_api.HttpBackendRef(
                            name=get_service_name(args, component_name),
                            port=networking.get_port_number(http_route_spec.port)
                        )]
                    )]
                )
            )
            manifests.append(http_route.dump_for_dd())

            policy_ports.add(http_route_spec.port)

        policy_port_objects = []
        assert networking.ports is not None
        for port in policy_ports:
            port_definition = networking.ports[port]
            if isinstance(port_definition, int):
                policy_port_objects.append(client.V1NetworkPolicyPort(
                    protocol=NETWORKING_DEFAULT_PROTOCOL,
                    port=port_definition
                ))
            else:
                policy_port_objects.append(client.V1NetworkPolicyPort(
                    protocol=port_definition.protocol,
                    port=port_definition.port
                ))

        network_policy = client.V1NetworkPolicy(
            api_version="networking.k8s.io/v1",
            kind="NetworkPolicy",
            metadata=client.V1ObjectMeta(
                name=get_network_policy_name(args, component_name),
                namespace=args.app_def.metadata.namespace,
                labels=args.app_labels.copy(),
                annotations=args.app_annotations.copy()
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
                                "kubernetes.io/metadata.name": args.app_def.defaults.networking.gateway.namespace
                            }),
                            pod_selector=client.V1LabelSelector(match_labels={
                                "gateway.networking.k8s.io/gateway-name": args.app_def.defaults.networking.gateway.name
                            })
                        )],
                        ports=policy_port_objects
                    )
                ]
            )
        )

        manifests.append(client.ApiClient().sanitize_for_serialization(network_policy))

    return manifests
