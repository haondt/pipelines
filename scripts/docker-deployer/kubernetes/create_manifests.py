from __future__ import annotations
from kubernetes import client
from types import SimpleNamespace
from typing import Any, Callable
from ..lib.environment import Environment
from .models import *
from ..lib.yaml_tools import deep_merge
from dataclasses import dataclass

APP_SELECTOR_NAME = 'deployment.haondt.dev/part-of'
COMPONENT_SELECTOR_NAME = 'deployment.haondt.dev/name'

@dataclass
class ManifestArguments:
    app_def: AppDefinition
    app_env: Environment
    app_labels: dict[str, str]
    component_labels_factory: Callable[[Component], dict[str, str]]
    app_annotations: dict[str, str]
    component_annotations_factory: Callable[[Component], dict[str, str]]

def get_app_labels(app_def: AppDefinition) -> dict[str, str]:
    app_labels: dict[str, str] = app_def.metadata.labels
    app_selector_value = app_def.metadata.name
    app_labels.setdefault(APP_SELECTOR_NAME, app_selector_value)
    return app_labels

def get_app_annotations(app_def: AppDefinition) -> dict[str, str]:
    return app_def.metadata.annotations

def get_component_labels_factory(app_def: AppDefinition, app_labels: dict[str, str]) -> Callable[[Component], dict[str, str]]:
    def fn(component: Component) -> dict[str, str]:
        component_labels = deep_merge(app_labels, component.metadata.labels)
        component_selector_value = component.metadata.name
        component_labels.setdefault(COMPONENT_SELECTOR_NAME, component_selector_value)
        return component_labels
    return fn

def get_component_annotations_factory(app_def: AppDefinition, app_annotations: dict[str, str]) -> Callable[[Component], dict[str, str]]:
    def fn(component: Component) -> dict[str, str]:
        component_annotations = deep_merge(app_annotations, component.metadata.annotations)
        return component_annotations
    return fn

def create_deployment_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    manifests = []

    for component_name, component in args.app_def.spec.components.items():
        component_labels = args.component_labels_factory(component)
        component_annotations = args.component_annotations_factory(component)
        image = component.spec.image
        
        resources_dict = {}
        if component.resources:
            if component.resources.limits:
                resources_dict['limits'] = component.resources.limits.model_dump(exclude_none=True)
            if component.resources.requests:
                resources_dict['requests'] = component.resources.requests.model_dump(exclude_none=True)
        
        container = client.V1Container(
            name=component_name,
            image=image,
            resources=client.V1ResourceRequirements(**resources_dict) if resources_dict else None
        )
        
        
        # Create pod template spec
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=component_labels, annotations=component_annotations),
            spec=client.V1PodSpec(containers=[container])
        )
        
        # Create deployment spec
        deployment_spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={
                APP_SELECTOR_NAME: args.app_labels[APP_SELECTOR_NAME],
                COMPONENT_SELECTOR_NAME: component_labels[COMPONENT_SELECTOR_NAME]
            }),
            template=pod_template
        )
        
        # Create deployment
        deployment = client.V1Deployment(
            api_version='apps/v1',
            kind='Deployment',
            metadata=client.V1ObjectMeta(
                name=f"{args.app_def.metadata.name}-{component_name}",
                namespace=args.app_def.metadata.namespace,
                labels=component_labels,
                annotations=component_annotations
            ),
            spec=deployment_spec
        )

        
        # Convert to dictionary for output
        manifests.append(client.ApiClient().sanitize_for_serialization(deployment))

    return manifests

def create_namespace_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    ns = client.V1Namespace(
        api_version="v1",
        kind="Namespace",
        metadata=client.V1ObjectMeta(
            name=args.app_def.metadata.namespace,
            labels=args.app_labels,
            annotations=args.app_def.metadata.annotations,
        ),
    )
    return [client.ApiClient().sanitize_for_serialization(ns)] # type: ignore[no-any-return]

def create_manifests(app_def: AppDefinition, app_env: Environment) -> list[dict[str, Any]]:
    app_labels: dict[str, str] = get_app_labels(app_def)
    app_annotations: dict[str, str] = get_app_annotations(app_def)
    args = ManifestArguments(
        app_def=app_def,
        app_env=app_env,
        app_labels=app_labels,
        component_labels_factory=get_component_labels_factory(app_def, app_labels),
        app_annotations=app_annotations,
        component_annotations_factory=get_component_annotations_factory(app_def, app_annotations),
    )
    manifests = []
    manifests += create_deployment_manifests(args)
    manifests += create_namespace_manifests(args)

    return manifests
