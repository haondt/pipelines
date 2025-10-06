from .models import ComponentManifestArguments
from ..models import *
from ..utils import coerce_dns_name, make_config_map_key
from ...lib.render_template import render_template
from typing import Any
from kubernetes import client

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
                'namespace': args.app_def.metadata.namespace
            },
            'spec': {
                'config': rendered_config
            }
        }
        manifests.append(partial_config)

    return manifests
