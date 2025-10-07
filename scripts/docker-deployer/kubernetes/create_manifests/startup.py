from .models import ComponentManifestArguments
from ..models import *
import json
from ..utils import coerce_dns_name, generate_stable_id
from typing import Any
from kubernetes import client

def create_startup_init_containers(args: ComponentManifestArguments, tasks: list[StartupTask], volume_mounts: list[client.V1VolumeMount] | None ) -> list[client.V1Container]:
    containers: list[client.V1Container] = []
    additional_manifests = []

    for task in tasks:
        if task.chown is not None:
            command = ["chown"]

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
        elif task.chmod is not None:
            command = ["chmod"]

            if task.chmod.recursive:
                command.append("-R")
            command.append(task.chmod.mode)

            name = 'startup-chmod-'
            if task.chmod.path:
                command.append(task.chmod.path)
                if not task.chmod.paths:
                    name += coerce_dns_name(task.chmod.path) + "-"
            if task.chmod.paths:
                command += task.chmod.paths

            if task.chmod.path is None and not task.chmod.paths:
                raise ValueError(f'At least one path must be specified')

            name += generate_stable_id(task.chmod)

            containers.append(client.V1Container(
                name=name,
                image=args.app_def.defaults.images.startup_tasks_chmod,
                command=command,
                volume_mounts=volume_mounts
            ))
        elif task.chgrp is not None:
            command = ["chgrp"]

            if task.chgrp.recursive:
                command.append("-R")
            command.append(str(task.chgrp.group))

            name = 'startup-chgrp-'
            if task.chgrp.path:
                command.append(task.chgrp.path)
                if not task.chgrp.paths:
                    name += coerce_dns_name(task.chgrp.path) + "-"
            if task.chgrp.paths:
                command += task.chgrp.paths

            if task.chgrp.path is None and not task.chgrp.paths:
                raise ValueError(f'At least one path must be specified')

            name += generate_stable_id(task.chgrp)

            containers.append(client.V1Container(
                name=name,
                image=args.app_def.defaults.images.startup_tasks_chgrp,
                command=command,
                volume_mounts=volume_mounts
            ))
        elif task.gomplate is not None:
            command = ["gomplate"]

            if task.gomplate.input.file:
                command += ['--file', task.gomplate.input.file]
            elif task.gomplate.input.files:
                for file in task.gomplate.input.files:
                    command += ['--file', file]
            elif task.gomplate.input.dir:
                command += ['--input-dir', task.gomplate.input.dir]
            else:
                raise ValueError(f'Using unknown input file type {task.gomplate.input}')

            if task.gomplate.output.file:
                command += ['--out', task.gomplate.output.file]
            elif task.gomplate.output.files:
                for file in task.gomplate.output.files:
                    command += ['--out', file]
            elif task.gomplate.output.dir:
                command += ['--output-dir', task.gomplate.output.dir]
            else:
                raise ValueError(f'Using unknown output file type {task.gomplate.output}')

            if task.gomplate.data_sources:
                for k, v in task.gomplate.data_sources.items():
                    command += ['--datasource', f'{k}={v}']

            if task.gomplate.extra_args:
                command += task.gomplate.extra_args


            name = f'startup-gomplate-{generate_stable_id(task.gomplate)}'

            containers.append(client.V1Container(
                name=name,
                image=args.app_def.defaults.images.startup_tasks_gomplate,
                command=command,
                volume_mounts=volume_mounts
            ))
        elif task.busybox is not None:
            command = ["sh", "-c", task.busybox.script]

            name = f'startup-busybox-{generate_stable_id(task.busybox)}'
            containers.append(client.V1Container(
                name=name,
                image=args.app_def.defaults.images.startup_tasks_busybox,
                command=command,
                volume_mounts=volume_mounts
            ))
        else:
            raise ValueError(f'Unsupported startup.task type {task}')

    return containers
