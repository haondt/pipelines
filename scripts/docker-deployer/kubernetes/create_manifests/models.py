from dataclasses import dataclass
from ..models import *
from ...lib.environment import Environment
from typing import Callable

APP_SELECTOR_NAME = 'deployment.haondt.dev/part-of'
NAMESPACE_SELECTOR_NAME = 'deployment.haondt.dev/name'
COMPONENT_SELECTOR_NAME = 'deployment.haondt.dev/name'
PROJECT_SELECTOR_NAME = 'deployment.haondt.dev/project'
SERVICE_DEFAULT_PORT = 8080

@dataclass
class ManifestArguments:
    app_def: AppDefinition
    app_env: Environment
    app_labels: dict[str, str]
    component_labels_factory: Callable[[Component], dict[str, str]]
    app_annotations: dict[str, str]
    component_annotations_factory: Callable[[Component], dict[str, str]]
    compiled_files_dir: str

@dataclass
class ComponentManifestArguments:
    app_def: AppDefinition
    app_env: Environment
    app_labels: dict[str, str]
    component_labels: dict[str, str]
    app_annotations: dict[str, str]
    component_annotations: dict[str, str]
    compiled_files_dir: str
