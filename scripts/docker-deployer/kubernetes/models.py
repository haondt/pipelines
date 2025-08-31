from pydantic import BaseModel, Field
from kubernetes import client
from typing import Any

# Resource specifications
class ResourceSpec(BaseModel):
    cpu: str | None = None
    memory: str | None = None

class Resources(BaseModel):
    limits: ResourceSpec | None = None
    requests: ResourceSpec | None = None

# Volume specifications
class ConfigMapSource(BaseModel):
    source: str | dict[str, Any]

class SecretSource(BaseModel):
    source: dict[str, Any]

class VolumeSpec(BaseModel):
    path: str | None = None
    env: bool | None = None

    configMap: ConfigMapSource | None = None
    secret: SecretSource | None = None

# Networking specifications
class TLSConfig(BaseModel):
    enabled: bool = False
    host: str | None = None

class IngressConfig(BaseModel):
    enabled: bool = False
    host: str | None = None
    port: int | None = None
    tls: TLSConfig | None = None

class NetworkingSpec(BaseModel):
    dependencies: list[str] | None = None
    ingress: IngressConfig | None = None

class ComponentNetworking(BaseModel):
    ingress: IngressConfig | None = None

# Component spec
class ComponentSpec(BaseModel):
    image: str
    networking: NetworkingSpec | None = None
    volumes: dict[str, VolumeSpec] | None = None

# Metadata can be either a string shorthand or a full object
class ComponentMetadata(BaseModel):
    component: str | None = None
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    name: str

# Full component definition
class Component(BaseModel):
    metadata: ComponentMetadata
    networking: ComponentNetworking | None = None
    resources: Resources | None = None
    spec: ComponentSpec
    
    # Custom fields that might be in your YAML
    class Config:
        extra = "allow"  # Allow extra fields like x-tl

# Top-level spec
class AppSpec(BaseModel):
    components: dict[str, Component]

# App metadata
class AppMetadata(BaseModel):
    annotations: dict[str, str] = {}
    labels: dict[str, str] = {}
    namespace: str
    name: str

# Root app definition
class AppDefinition(BaseModel):
    metadata: AppMetadata
    spec: AppSpec


def validate_app_yaml(app_yaml: dict) -> AppDefinition:
    return AppDefinition.model_validate(app_yaml)
