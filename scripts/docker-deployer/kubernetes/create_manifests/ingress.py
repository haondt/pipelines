from sys import api_version
from .models import *
from typing import Any
from kubernetes import client
import os
from ..utils import coerce_dns_name, hash_str
from .service import get_service_name

def get_ingress_name(args: ManifestArguments, component_name: str, host: str):
    return f"{args.app_def.metadata.name}-{component_name}-{coerce_dns_name(host)}"
def get_network_policy_name(args: ManifestArguments, component_name: str, host: str, port: str):
    return f"{args.app_def.metadata.name}-{component_name}-ingress-{coerce_dns_name(host)}-{port}"

def create_ingress_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.spec.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)

        networking = component.spec.networking
        if not networking or not networking.ingresses:
            continue

        for ingress_spec in networking.ingresses:
            if not ingress_spec.enabled:
                continue

            ingress = client.V1Ingress(
                api_version="networking.k8s.io/v1",
                kind="Ingress",
                metadata=client.V1ObjectMeta(
                    name=get_ingress_name(args, component_name, ingress_spec.host),
                    namespace=args.app_def.metadata.namespace,
                    labels=component_labels,
                    annotations=component_annotations | { 'cert-manager.io/cluster-issuer': 'letsencrypt-prod' }
                ),
                spec=client.V1IngressSpec(
                    ingress_class_name=INGRESS_CLASS_NAME,
                    rules=[client.V1IngressRule(
                        host=ingress_spec.host,
                        http=client.V1HTTPIngressRuleValue(
                            paths=[client.V1HTTPIngressPath(
                                path="/",
                                path_type="Prefix",
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        name=get_service_name(args, component_name, ingress_spec.port),
                                        port=client.V1ServiceBackendPort(
                                            number=SERVICE_DEFAULT_PORT
                                        )
                                    )
                                )
                            )]
                        )
                    )]
                )
            )

            if ingress_spec.tls.enabled:
                # make the compiler happy
                assert ingress.spec is not None
                assert ingress_spec.tls.host is not None

                ingress.spec.tls = [client.V1IngressTLS(
                    hosts=[ingress_spec.tls.host],
                    secret_name=coerce_dns_name(ingress_spec.tls.host + "-" + hash_str(ingress_spec.tls.host, 8))
                )]

            network_policy = client.V1NetworkPolicy(
                api_version="networking.k8s.io/v1",
                kind="NetworkPolicy",
                metadata=client.V1ObjectMeta(
                    name=get_network_policy_name(args, component_name, ingress_spec.host, ingress_spec.port),
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
                                    "app.kubernetes.io/name": "ingress-nginx"
                                })
                            )],
                            ports=[client.V1NetworkPolicyPort(
                                protocol=ingress_spec.protocol,
                                port=ingress_spec.port
                            )]
                        )
                    ]
                )
            )

            manifests.append(client.ApiClient().sanitize_for_serialization(ingress))
            manifests.append(client.ApiClient().sanitize_for_serialization(network_policy))
    return manifests
