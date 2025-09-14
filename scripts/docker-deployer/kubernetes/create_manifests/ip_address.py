from .models import *
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name, hash_str

def get_ip_address_service_name(args: ManifestArguments, component_name: str, ip_address: str, port_names: list[str]):
    return f"{args.app_def.metadata.name}-{component_name}-ip-{hash_str(ip_address, 6)}-{'-'.join(port_names)}"
def get_ip_address_network_policy_name(args: ManifestArguments, component_name: str, ip_address: str, port_names: list[str]):
    return f"{args.app_def.metadata.name}-{component_name}-ingress-ip-{hash_str(ip_address, 6)}-{'-'.join(port_names)}"

def create_ip_address_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)

        networking = component.networking
        if not networking or not networking.ip_addresses:
            continue

        for ip_address_spec in networking.ip_addresses:
            service_ports: list[client.V1ServicePort] = []
            network_policy_ports: list[client.V1NetworkPolicyPort] = []
            default_port = SERVICE_DEFAULT_PORT
            default_protocol = 'TCP'
            for port in ip_address_spec.ports:
                port_port = default_port
                port_protocol = default_protocol
                if networking.ports is not None \
                    and port in networking.ports:
                    networking_port = networking.ports[port]
                    if isinstance(networking_port, int):
                        port_port = networking_port
                    else:
                        port_port = networking_port.port
                        port_protocol = networking_port.protocol

                service_ports.append(client.V1ServicePort(
                    protocol=port_protocol,
                    port=port_port,
                    target_port=port_port,
                    name=port
                ))
                network_policy_ports.append(client.V1NetworkPolicyPort(
                    protocol=port_protocol,
                    port=port
                ))

            service = client.V1Service(
                api_version= "v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=get_ip_address_service_name(args, component_name, ip_address_spec.ip, ip_address_spec.ports),
                    namespace=args.app_def.metadata.namespace,
                    labels=component_labels,
                    annotations=component_annotations | {
                        "metallb.io/loadBalancerIPs": ip_address_spec.ip
                    }
                ),
                spec=client.V1ServiceSpec(
                    type="LoadBalancer",
                    selector={
                        APP_SELECTOR_NAME: component_labels[APP_SELECTOR_NAME],
                        COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME],
                        PROJECT_SELECTOR_NAME: component_labels[PROJECT_SELECTOR_NAME],
                    },
                    ports=service_ports
                )
            )


            network_policy = client.V1NetworkPolicy(
                api_version="networking.k8s.io/v1",
                kind="NetworkPolicy",
                metadata=client.V1ObjectMeta(
                    name=get_ip_address_network_policy_name(args, component_name, ip_address_spec.ip, ip_address_spec.ports),
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
                                ip_block=client.V1IPBlock(cidr="0.0.0.0/0")
                            )],
                            ports=network_policy_ports
                        )
                    ]
                )
            )

            manifests.append(client.ApiClient().sanitize_for_serialization(service))
            manifests.append(client.ApiClient().sanitize_for_serialization(network_policy))
    return manifests
