from .models import ManifestArguments
from ..models import *
from ...lib.environment import Environment
from .app import get_app_labels, get_app_annotations
from .component import get_component_labels_factory, get_component_annotations_factory
from .deployment import create_deployment_manifests
from .namespace import create_namespace_manifests
from .service import create_service_manifests
from .network_policy import create_network_policy_manifests
from .ingress import create_ingress_manifests
from .ip_address import create_ip_address_manifests
from .rathole import create_rathole_manifests

from typing import Any


def create_manifests(app_def: AppDefinition, app_env: Environment, compiled_files_dir) -> list[dict[str, Any]]:
    app_labels: dict[str, str] = get_app_labels(app_def)
    app_annotations: dict[str, str] = get_app_annotations(app_def)
    args = ManifestArguments(
        app_def=app_def,
        app_env=app_env,
        app_labels=app_labels,
        component_labels_factory=get_component_labels_factory(app_def, app_labels),
        app_annotations=app_annotations,
        component_annotations_factory=get_component_annotations_factory(app_def, app_annotations),
        compiled_files_dir=compiled_files_dir
    )
    manifests = []
    manifests += create_deployment_manifests(args)
    manifests += create_namespace_manifests(args)
    manifests += create_service_manifests(args)
    manifests += create_network_policy_manifests(args)
    manifests += create_ingress_manifests(args)
    manifests += create_ip_address_manifests(args)
    manifests += create_rathole_manifests(args)

    return manifests
