from pydantic_core.core_schema import none_schema
from .models import *
from .volume import create_volume_manifest
from .environment import create_environment_manifest
from typing import Any
from kubernetes import client
import copy
import os
from ..utils import coerce_dns_name, generate_stable_id, hash_str, make_config_map_key
from ...lib.yaml_tools import deep_merge
from .service import get_service_name
from .startup import create_startup_init_containers

def create_charon_manifests(args: ComponentManifestArguments, configs: list[CharonConfig], deployment: client.V1Deployment, component_volumes: list[client.V1Volume]) -> list[dict[str, Any]]:
    assert deployment.metadata is not None
    assert deployment.spec is not None

    manifests = []

    base_overlays = {k: v.model_dump(mode='json') for k, v in args.app_def.defaults.charon.overlays.items()}

    for config in configs:
        config_obj = {}
        for overlay_name in config.overlays:
            overlay = base_overlays[overlay_name]
            config_obj = deep_merge(config_obj, overlay, overwrite_with_none=False)
        config_obj = deep_merge(config_obj, config.model_dump(mode='json'), overwrite_with_none=False)
        config = CharonConfig.model_validate(config_obj)

        assert config.name is not None
        backup_job_name = f'{args.component_name}-{config.name}-{generate_stable_id(config)}'
        job_name = f'charon-{backup_job_name}'

        backup_job = {
            'apiVersion': 'charon.haondt.dev/v1',
            'kind': 'BackupJob',
            'metadata': {
                "name": backup_job_name,
                "namespace": args.app_def.metadata.namespace
            },
            'spec': {
                'name': config.name,
                'repositoryConfigs': []
            }
        }
        service_account_name = job_name
        service_account = client.V1ServiceAccount(
            api_version="v1",
            kind="ServiceAccount",
            metadata=client.V1ObjectMeta(
                name=service_account_name,
                namespace=args.app_def.metadata.namespace
            )
        )
        job_spec = client.V1JobSpec(
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    name=job_name
                ),
                spec=client.V1PodSpec(
                    service_account_name=service_account_name,
                    restart_policy='OnFailure',
                    volumes=[],
                    containers=[client.V1Container(
                        name='primary',
                        image=args.app_def.defaults.images.charon_k8s_job,
                        volume_mounts=[],
                        env=[
                            client.V1EnvVar(
                                name='CHARON_BACKUPJOB_NAME',
                                value=backup_job_name
                            ),
                            client.V1EnvVar(
                                name='CHARON_BACKUPJOB_NAMESPACE',
                                value=args.app_def.metadata.namespace
                            ),
                            client.V1EnvVar(
                                name='CHARON_BACKUPJOB_MODE',
                                value='backup'
                            )
                        ]
                    )]
                )
            )
        )
        assert job_spec.template is not None and job_spec.template.spec is not None and job_spec.template.spec.containers is not None and job_spec.template.spec.volumes is not None

        if config.repository_configs:
            for repository_config in config.repository_configs:
                if repository_config.config_map:
                    item = {
                        'configMap': {
                            'name': repository_config.config_map.name,
                            'namespace': repository_config.config_map.namespace,
                            'key': repository_config.config_map.key
                        }
                    }
                elif repository_config.secret:
                    item = {
                        'secret': {
                            'name': repository_config.secret.name,
                            'namespace': repository_config.secret.namespace,
                            'key': repository_config.secret.key
                        }
                    }
                elif repository_config.raw:
                    item = {'raw':repository_config.raw}
                else:
                    raise ValueError(f'Couldn\'t interpret repository config {repository_config}')

                backup_job['spec']['repositoryConfigs'].append(item)

        if config.volumes:
            for config_volume in config.volumes:
                if config_volume.secret:
                    volume_name = coerce_dns_name(f'{config_volume.secret.name}-{config_volume.secret.key}-{generate_stable_id(config_volume.secret)}')
                    local_secret_name=f'{config_volume.secret.namespace}-{config_volume.secret.name}-mirror'
                    
                    mirrored_secret = client.V1Secret(
                        api_version="v1",
                        kind="Secret",
                        metadata=client.V1ObjectMeta(
                            name=local_secret_name,
                            namespace=args.app_def.metadata.namespace,
                            annotations={
                                'reflector.v1.k8s.emberstack.com/reflects': f'{config_volume.secret.namespace}/{config_volume.secret.name}',
                                'reflector.v1.k8s.emberstack.com/reflected-version': ''
                            }
                        )
                    )
                    manifests.append(client.ApiClient().sanitize_for_serialization(mirrored_secret))

                    if config_volume.dest.file:
                        volume_source_items = [client.V1KeyToPath(
                            key=config_volume.secret.key,
                            path=os.path.basename(config_volume.dest.file)
                        )]
                        volume_mount = client.V1VolumeMount(
                            name=volume_name,
                            mount_path=config_volume.dest.file,
                            sub_path=os.path.basename(config_volume.dest.file),
                            read_only=True
                        )
                    else:
                        raise ValueError(f'Unable to handle volume dest config {config_volume.dest}')

                    job_spec.template.spec.volumes.append(client.V1Volume(
                        name=volume_name,
                        secret=client.V1SecretVolumeSource(
                            secret_name=local_secret_name,
                            items=volume_source_items
                        )
                    ))
                    job_spec.template.spec.containers[0].volume_mounts.append(volume_mount)
                else:
                    raise ValueError(f'Couldn\'t interpret volume config {config_volume}')

        if config.source:
            if config.source.volumes:
                raw_config = 'type: local\npaths:\n'
                for k, v in config.source.volumes.items():
                    base_path = f'/mnt/src/{make_config_map_key(k)}'
                    for sub_path in v:
                        raw_config += f'  - {base_path}{sub_path}\n'

                    # volume_spec = volume_specs[k]
                    component_volume = None
                    for v in component_volumes:
                        if v.name == k:
                            component_volume = v
                            break
                    if component_volume == None:
                        raise ValueError(f'could not find volume {k} in component spec')
                    job_spec.template.spec.volumes.append(copy.deepcopy(component_volume))
                    job_spec.template.spec.containers[0].volume_mounts.append(client.V1VolumeMount(
                        mount_path=base_path,
                        name=k
                    ))

                item = {'raw':raw_config}

                # for volume jobs we want pod affinity with the deployment
                # to play nice with ReadWriteOnce PVCs
                job_spec.template.spec.affinity = client.V1Affinity(
                     pod_affinity=client.V1PodAffinity(
                         required_during_scheduling_ignored_during_execution=[client.V1PodAffinityTerm(
                             label_selector=deployment.spec.selector,
                             topology_key='kubernetes.io/hostname'
                         )]
                     )
                )


            else:
                raise ValueError(f'Couldn\'t interpret source config {config.source}')
            backup_job['spec']['sourceConfig'] = item

        if config.scale_down_deployment:
            backup_job['spec']['scale_down_deployments'] = [{
                'name': deployment.metadata.name,
                'namespace': deployment.metadata.namespace
            }]

        if config.schedule:
            cron_job = client.V1CronJob(
                api_version='batch/v1',
                kind='CronJob',
                metadata=client.V1ObjectMeta(
                    name=job_name,
                    namespace=deployment.metadata.namespace
                ),
                spec=client.V1CronJobSpec(
                    schedule=config.schedule,
                    concurrency_policy='Forbid',
                    successful_jobs_history_limit=3,
                    failed_jobs_history_limit=1,
                    job_template=client.V1JobTemplateSpec(spec=job_spec)
                )
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(cron_job))
        else:
            job_spec.ttl_seconds_after_finished = 3600
            job = client.V1Job(
                api_version='batch/v1',
                kind='Job',
                metadata=client.V1ObjectMeta(
                    name=job_name,
                    namespace=deployment.metadata.namespace
                ),
                spec=job_spec
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(job))


        # manifests.append(config.model_dump(mode='json'))
        manifests.append(backup_job)
        manifests.append(client.ApiClient().sanitize_for_serialization(service_account))

    return manifests

