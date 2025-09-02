from ..models import *
from .models import NAMESPACE_SELECTOR_NAME, ManifestArguments
from typing import Any
from kubernetes import client

def create_namespace_manifests(args: ManifestArguments) -> list[dict[str, Any]]:
    ns = client.V1Namespace(
        api_version="v1",
        kind="Namespace",
        metadata=client.V1ObjectMeta(
            name=args.app_def.metadata.namespace,
            labels=args.app_labels | { NAMESPACE_SELECTOR_NAME: args.app_def.metadata.namespace },
            annotations=args.app_def.metadata.annotations,
        ),
    )
    return [client.ApiClient().sanitize_for_serialization(ns)] # type: ignore[no-any-return]
