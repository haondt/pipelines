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

    for component_name, component in args.app_def.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)

        networking = component.networking
        if not networking or not networking.ingresses:
            continue

        for ingress_spec in networking.ingresses:
            if not ingress_spec.enabled:
                continue

            ingress_annotations = component_annotations.copy()

            if ingress_spec.nginx:
                if ingress_spec.nginx.proxy_body_size:
                    ingress_annotations['nginx.ingress.kubernetes.io/proxy-body-size'] = ingress_spec.nginx.proxy_body_size

            ingress = client.V1Ingress(
                api_version="networking.k8s.io/v1",
                kind="Ingress",
                metadata=client.V1ObjectMeta(
                    name=get_ingress_name(args, component_name, ingress_spec.host),
                    namespace=args.app_def.metadata.namespace,
                    labels=component_labels,
                    annotations=ingress_annotations
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

                if ingress_spec.tls.host is not None:
                    tls_host = ingress_spec.tls.host
                elif args.app_def.defaults.networking is not None \
                    and args.app_def.defaults.networking.tls is not None \
                    and args.app_def.defaults.networking.tls.host is not None:
                    default_host_spec = args.app_def.defaults.networking.tls.host
                    if isinstance(default_host_spec, str):
                        tls_host = default_host_spec
                    elif default_host_spec.wildcard:
                        if '.' not in ingress_spec.host:
                            raise ValueError(f'Cannot determine wildcard host as the ingress host \'{ingress_spec.host}\' does not contain \'.\'')
                        tls_host = '*.' + ingress_spec.host.split('.', 1)[1]
                    else:
                        raise ValueError(f'default host spec was not in the expected format {default_host_spec}')
                else:
                    raise ValueError(f'Ingress tls is enabled but could not find a host definition {ingress_spec.tls}')


                def get_default_secret_name():
                    return get_ingress_name(args, component_name, ingress_spec.host) + '-tls'
                    # TODO: one day: we can use this as the name instead and deduplicate the secrets
                    # return coerce_dns_name(tls_host + "-" + hash_str(tls_host, 8))
                mirror_source = None
                secret_name = None
                create_secret = None
                if ingress_spec.tls.secret is not None:
                    if isinstance(ingress_spec.tls.secret, str):
                        secret_name = ingress_spec.tls.secret
                    elif ingress_spec.tls.secret.mirror is not None:
                        mirror_source = ingress_spec.tls.secret.mirror
                        secret_name = get_default_secret_name()
                    elif ingress_spec.tls.secret.create:
                        create_secret = True
                        secret_name = get_default_secret_name()
                if secret_name is None and args.app_def.defaults.networking is not None \
                    and args.app_def.defaults.networking.tls is not None \
                    and args.app_def.defaults.networking.tls.secret is not None:
                    default_secret_spec = args.app_def.defaults.networking.tls.secret
                    if isinstance(default_secret_spec, str):
                        secret_name = default_secret_spec
                    elif default_secret_spec.create:
                        secret_name = get_default_secret_name()
                        create_secret = True
                    elif default_secret_spec.mirror:
                        mirror_source = default_secret_spec.mirror
                        secret_name = get_default_secret_name()
                    elif default_secret_spec.from_host:
                        for from_host_spec in default_secret_spec.from_host:
                            if from_host_spec.host == tls_host:
                                if isinstance(from_host_spec.value, str):
                                    secret_name = from_host_spec.value
                                elif from_host_spec.value.create:
                                    secret_name = get_default_secret_name()
                                    create_secret = True
                                elif from_host_spec.value.mirror:
                                    mirror_source = from_host_spec.value.mirror
                                    secret_name = get_default_secret_name()
                                break

                if secret_name is None:
                    raise ValueError(f'Failed to extract secret name from tls.secret configuration {ingress_spec},{args.app_def.defaults.networking}')

                if create_secret:
                    assert ingress.metadata is not None
                    ingress.metadata.annotations['cert-manager.io/cluster-issuer'] = 'letsencrypt-prod'

                if mirror_source is not None:
                    manifests.append(client.ApiClient().sanitize_for_serialization(client.V1Secret(
                        api_version="v1",
                        kind="Secret",
                        type="kubernetes.io/tls",
                        metadata=client.V1ObjectMeta(
                            name=secret_name,
                            namespace=args.app_def.metadata.namespace,
                            annotations={
                                'reflector.v1.k8s.emberstack.com/reflects': mirror_source,
                                'reflector.v1.k8s.emberstack.com/reflected-version': ''
                            }
                        ),
                        data={'tls.key': '', 'tls.crt': ''}
                    )))

                ingress.spec.tls = [client.V1IngressTLS(
                    hosts=[tls_host],
                    secret_name=secret_name
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
