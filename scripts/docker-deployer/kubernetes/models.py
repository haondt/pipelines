from pydantic import BaseModel, model_validator, Field
import uuid

# Resource specifications
class ResourceSpec(BaseModel):
    cpu: str | None = None
    memory: str | None = None

class Resources(BaseModel):
    limits: ResourceSpec | None = None
    requests: ResourceSpec | None = None

# Volume specifications
class VolumeSource(BaseModel):
    glob: str | None = None
    dir: str | None = None
    file: str | None = None
    data: str | None = None
    secret: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.glob,
            self.dir,
            self.file,
            self.data,
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self

    def is_single(self):
        return (self.file is not None) or (self.data is not None)

    def human_name(self) -> str:
        return self.glob or self.dir or self.file or self.data or "VolumeSource"

class VolumeDestination(BaseModel):
    file: str | None = None
    dir: str | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.file,
            self.dir,
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self

    def is_single(self):
        return self.file is not None

class VolumeSpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4().hex))

    src: VolumeSource
    dest: VolumeDestination

    @model_validator(mode="after")
    def validate_destination_type(self):
        if self.src.is_single():
            if not self.dest.is_single():
                raise ValueError("Src and dest must either both be single or both be not single")
        elif self.dest.is_single():
            raise ValueError("Src and dest must either both be single or both be not single")
        return self

    def is_single(self):
        return self.src.is_single()

class EnvironmentSpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4().hex))

    file: str | None = None
    raw: dict[str, str | bool | float | int | None] | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.file,
            self.raw,
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self


    secret: bool = Field(default=False)

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
    volumes: list[VolumeSpec] | None = None
    environment: list[EnvironmentSpec] | None = None

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
