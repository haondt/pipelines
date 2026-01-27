from sys import api_version
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
from .startup import create_startup_init_containers
_api_client = client.ApiClient()


def create_gluetun_component_manifests(args: ComponentManifestArguments, networking: NetworkingSpec, config: GluetunConfig, deployment: client.V1Deployment) -> list[dict[str, Any]]:
    assert deployment.metadata is not None
    assert deployment.spec is not None
    assert deployment.spec.template is not None
    assert deployment.spec.template.spec is not None

    manifests = []

    pod_spec: client.V1PodSpec = deployment.spec.template.spec

    if pod_spec.volumes is None:
        pod_spec.volumes = []
    volume_name = None
    for volume in pod_spec.volumes:
        if volume.host_path is not None \
            and volume.host_path.path == '/dev/net/tun' \
            and volume.host_path.type == 'CharDevice':
            volume_name = volume.name
            break
    if volume_name is None:
        volume_name = 'dev-net-tun'
        pod_spec.volumes.append(client.V1Volume(
            name=volume_name,
            host_path=client.V1HostPathVolumeSource(
                path='/dev/net/tun',
                type='CharDevice'
            )
        ))

    secret_env = {}
    config_map_env = {}
    if config.wireguard:
        secret_env['WIREGUARD_PRIVATE_KEY'] = config.wireguard.private_key
        config_map_env['VPN_TYPE'] = 'wireguard'
        if config.wireguard.mtu is not None:
            config_map_env['WIREGUARD_MTU'] = config.wireguard.mtu
    else:
        raise ValueError(f'Error while configuring component {args.component_name}: only wireguard is supported for gluetun vpn type')

    if config.protonvpn is not None:
        config_map_env['VPN_SERVICE_PROVIDER'] = 'protonvpn'
        if config.port_forwarding is not None:
            config_map_env['PORT_FORWARD_ONLY'] = 'on'
        config_map_env['FREE_ONLY'] = 'on' if config.protonvpn.free else 'off'
        config_map_env['SERVER_COUNTRIES'] = ','.join(config.protonvpn.server_countries)

    if config.port_forwarding is not None:
        config_map_env['VPN_PORT_FORWARDING'] = 'on' if config.port_forwarding else 'off'
        if config.port_forwarding.up_command is not None:
            config_map_env['VPN_PORT_FORWARDING_UP_COMMAND'] = config.port_forwarding.up_command
        if config.port_forwarding.down_command is not None:
            config_map_env['VPN_PORT_FORWARDING_DOWN_COMMAND'] = config.port_forwarding.down_command
        if config.port_forwarding.listening_port is not None:
            config_map_env['VPN_PORT_FORWARDING_LISTENING_PORT'] = config.port_forwarding.listening_port
    if config.dns is not None:
        if config.dns.upstream_resolvers is not None and len(config.dns.upstream_resolvers) > 0:
            config_map_env['DNS_UPSTREAM_RESOLVERS'] = ','.join(config.dns.upstream_resolvers)
    if config.firewall is not None:
        if config.firewall.input_ports:
            config_map_env['FIREWALL_INPUT_PORTS'] = ','.join([str(networking.get_port_number(i)) for i in config.firewall.input_ports])
        if config.firewall.outbound_subnets:
            config_map_env['FIREWALL_OUTBOUND_SUBNETS'] = ','.join([str(networking.get_port_number(i)) for i in config.firewall.outbound_subnets])

    env_secret_or_config_map_name = f'{args.app_def.metadata.name}-{args.component_name}-gluetun-environment'
    env_secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        type="Opaque",
        metadata=client.V1ObjectMeta(
            name=env_secret_or_config_map_name,
            namespace=args.app_def.metadata.namespace,
            labels=args.component_labels,
            annotations=args.component_annotations,
        ),
        string_data=secret_env
    )
    env_config_map = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(
            name=env_secret_or_config_map_name,
            namespace=args.app_def.metadata.namespace,
            labels=args.component_labels,
            annotations=args.component_annotations,
        ),
        data=config_map_env
    )
    manifests.append(_api_client.sanitize_for_serialization(env_secret))
    manifests.append(_api_client.sanitize_for_serialization(env_config_map))


    if pod_spec.init_containers is None:
        pod_spec.init_containers = []
    pod_spec.init_containers.append(client.V1Container(
        name='gluetun',
        image=args.app_def.defaults.images.gluetun,
        restart_policy='Always',
        liveness_probe=client.V1Probe(
            _exec=client.V1ExecAction(command=['sh','-c','/gluetun-entrypoint healthcheck']),
            initial_delay_seconds=10,
            period_seconds=5,
            timeout_seconds=5,
            failure_threshold=15
        ),
        lifecycle=client.V1Lifecycle(
            post_start=client.V1LifecycleHandler(
                _exec=client.V1ExecAction(command=["/bin/sh", "-c", "(ip rule del table 51820; ip -6 rule del table 51820) || true"])
            )
        ),
        security_context=client.V1SecurityContext(capabilities=client.V1Capabilities(add=['NET_ADMIN'])),
        volume_mounts=[client.V1VolumeMount(name=volume_name,mount_path='/dev/net/tun')],
        env_from=[
            client.V1EnvFromSource(
                secret_ref=client.V1SecretEnvSource(
                    name=env_secret_or_config_map_name
                )
            ),
            client.V1EnvFromSource(
                config_map_ref=client.V1ConfigMapEnvSource(
                    name=env_secret_or_config_map_name
                )
            )
        ]
    ))


    return manifests

