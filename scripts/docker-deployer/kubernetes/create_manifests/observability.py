from .models import APP_SELECTOR_NAME, PROJECT_SELECTOR_NAME, COMPONENT_SELECTOR_NAME, ComponentManifestArguments
from ..models import *
from ..utils import coerce_dns_name, make_config_map_key
from ...lib.render_template import render_template
from typing import Any
from kubernetes import client
from .service import get_service_name

def create_observability_manifests(args: ComponentManifestArguments, obs: ObservabilitySpec) -> list[dict[str, Any]]:
    manifests = []

    if obs.alloy and obs.alloy.logs:
        job_name = coerce_dns_name(f'{args.app_def.metadata.namespace}-{args.app_def.metadata.name}-{args.component_name}').replace('-','_')
        crd_name = coerce_dns_name(f'{args.app_def.metadata.name}-{args.component_name}')

        kwargs = {
            'job_name': job_name,
            'namespace': args.app_def.metadata.namespace,
            'app_name': args.app_def.metadata.name,
            'component_name': args.component_name
        }
        if obs.alloy.logs.process:
            kwargs['process'] = obs.alloy.logs.process

        rendered_config = render_template('alloy.config.jinja', **kwargs)

        partial_config = {
            'apiVersion': 'alloy.haondt.dev/v1',
            'kind': 'AlloyPartialConfig',
            'metadata': { 
                'name': crd_name,
                'namespace': args.app_def.metadata.namespace,
                'labels': {
                    'deployment.haondt.dev/alloy-deployment': 'daemonset'
                }
            },
            'spec': {
                'config': rendered_config
            }
        }
        manifests.append(partial_config)

    if obs.probes and len(obs.probes) > 0:
        rendered_config = ''
        for probe_name, probe in obs.probes.items():
            crd_name = coerce_dns_name(f'{args.app_def.metadata.name}-{args.component_name}-probe-{probe_name}')
            if probe.http_get:
                if probe.alloy and probe.alloy.blackbox is not None:
                    rendered_config += render_template('alloy-blackbox-target.config.jinja',
                        name= crd_name.replace('-', '_'),
                        module='http_2xx',
                        address= f'{get_service_name(args, args.component_name, probe.http_get.port)}.{args.app_def.metadata.namespace}.svc.cluster.local:8080{probe.http_get.path}',
                        labels = {
                            "dev_haondt_app": args.app_def.metadata.name,
                            "dev_haondt_component": args.component_name,
                            "dev_haondt_namespace": args.app_def.metadata.namespace,
                            "dev_haondt_probe": probe_name
                        }
                    ) + "\n"

                    network_policy = client.V1NetworkPolicy(
                        api_version="networking.k8s.io/v1",
                        kind="NetworkPolicy",
                        metadata=client.V1ObjectMeta(
                            name=f'{args.app_def.metadata.name}-{args.component_name}-alloy-probe-{coerce_dns_name(probe_name)}',
                            namespace=args.app_def.metadata.namespace,
                        ),
                        spec=client.V1NetworkPolicySpec(
                            pod_selector=client.V1LabelSelector(match_labels={
                                APP_SELECTOR_NAME: args.component_labels[APP_SELECTOR_NAME],
                                COMPONENT_SELECTOR_NAME: args.component_labels[COMPONENT_SELECTOR_NAME],
                                PROJECT_SELECTOR_NAME: args.component_labels[PROJECT_SELECTOR_NAME],
                            }),
                            policy_types=["Ingress"],
                            ingress=[
                                client.V1NetworkPolicyIngressRule(
                                    _from=[client.V1NetworkPolicyPeer(
                                        namespace_selector=client.V1LabelSelector(match_labels={
                                            "kubernetes.io/metadata.name": "alloy"
                                        })
                                    )],
                                    ports=[client.V1NetworkPolicyPort(
                                        protocol='TCP',
                                        port=probe.http_get.port
                                    )]
                                )
                            ]
                        )
                    )
                    manifests.append(client.ApiClient().sanitize_for_serialization(network_policy))

                    partial_component = {
                        'apiVersion': 'alloy.haondt.dev/v1',
                        'kind': 'AlloyPartialComponent',
                        'metadata': { 
                            'name': crd_name,
                            'namespace': args.app_def.metadata.namespace,
                            'labels': {
                                'deployment.haondt.dev/alloy-deployment': 'deployment'
                            }
                        },
                        'spec': {
                            'label': 'default',
                            'component': 'prometheus.exporter.blackbox',
                            'config': rendered_config.strip()
                        }
                    }
                    manifests.append(partial_component)
            else:
                raise ValueError(f'Unknown probe config {probe}')


    return manifests
