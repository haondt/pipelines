from ..models import *
from .models import COMPONENT_SELECTOR_NAME
from ...lib.yaml_tools import deep_merge
from typing import Callable

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
