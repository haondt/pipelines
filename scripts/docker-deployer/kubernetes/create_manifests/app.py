from ..models import *
from .models import APP_SELECTOR_NAME

def get_app_labels(app_def: AppDefinition) -> dict[str, str]:
    app_labels: dict[str, str] = app_def.metadata.labels
    app_selector_value = app_def.metadata.name
    app_labels.setdefault(APP_SELECTOR_NAME, app_selector_value)
    return app_labels

def get_app_annotations(app_def: AppDefinition) -> dict[str, str]:
    return app_def.metadata.annotations
