from .models import ComponentManifestArguments
from ..models import *
import json
from ..utils import coerce_dns_name, generate_stable_id
from typing import Any
from kubernetes import client

def create_startup_init_containers(args: ComponentManifestArguments, tasks: list[StartupTask], volume_mounts: list[client.V1VolumeMount] | None ) -> list[client.V1Container]:
    containers: list[client.V1Container] = []

    for task in tasks:
        if task.chown is not None:
            command = ["sh", "-c", "chown"]
            if task.chown.recursive:
                command.append("-R")
            command.append(task.chown.owner)

            name = 'startup-chown-'
            if task.chown.path:
                command.append(task.chown.path)
                if not task.chown.paths:
                    name += coerce_dns_name(task.chown.path) + "-"
            if task.chown.paths:
                command += task.chown.paths

            if task.chown.path is None and not task.chown.paths:
                raise ValueError(f'At least one path must be specified')

            name += generate_stable_id(task.chown)

            containers.append(client.V1Container(
                name=name,
                image=args.app_def.defaults.images.startup_tasks_chown,
                command=command,
                volume_mounts=volume_mounts
            ))
        else:
            raise ValueError(f'Unsupported startup.task type {task}')

    return containers
