from pydantic import BaseModel, DirectoryPath, model_validator, Field
import uuid

def make_uppercase(values, key):
    if key in values and values[key]:
        values[key] = values[key].upper()
    return values

# Resource specifications
class ResourceSpec(BaseModel):
    cpu: str | None = None
    memory: str | None = None

class GpuConfig(BaseModel):
    enabled: bool = Field(default=False)
    resource_name: str = Field(default="nvidia.com/gpu")
    runtime_class_name: str = Field(default="nvidia")
    use_limit: bool = Field(default=False)


class Resources(BaseModel):
    limits: ResourceSpec | None = None
    requests: ResourceSpec | None = None
    gpu: GpuConfig = Field(default_factory=GpuConfig)

class PVCVolumeSource(BaseModel):
    storage_class: str | None = None
    size: str | None = None

class ScratchVolumeSource(BaseModel):
    size: str | None = None

class TmpfsVolumeSource(BaseModel):
    size: str | None = None

class HostVolumeSource(BaseModel):
    dir: str
    read_only: bool = Field(default=True)
    create: bool = Field(default=False)


# Volume specifications
class VolumeSource(BaseModel):
    glob: str | None = None
    dir: str | None = None
    file: str | None = None
    data: str | None = None
    secret: bool = Field(default=False)
    pvc: PVCVolumeSource | None = None
    host: HostVolumeSource | None = None
    scratch: ScratchVolumeSource | None = None
    tmpfs: TmpfsVolumeSource | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.glob,
            self.dir,
            self.file,
            self.data,
            self.pvc,
            self.host,
            self.tmpfs,
            self.scratch
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self

    def is_single(self):
        return any(i is not None for i in (self.file, self.data))

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
    secret: bool = Field(default=False)

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


class TlsSecretSource(BaseModel):
    create: bool | None = None
    mirror: str | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.create,
            self.mirror,
        ] if i is not None]

        if len(selected) > 1:
            raise ValueError(f"At most one type must be configured. found {selected}")
        return self

# Networking specifications
class TLSConfig(BaseModel):
    enabled: bool = Field(default=True)
    host: str | None = None
    secret: str | TlsSecretSource | None = None

class NginxConfig(BaseModel):
    proxy_body_size: str | None = None

class IngressConfig(BaseModel):
    enabled: bool = True
    host: str
    port: str
    protocol: str = Field(default='TCP')
    tls: TLSConfig = Field(default_factory=lambda: TLSConfig())
    nginx: NginxConfig = Field(default_factory=NginxConfig) 

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, values):
        make_uppercase(values, 'protocol')
        return values

class NetworkingDependency(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4().hex))
    name: str
    port: str | int
    app: str | None = None
    protocol: str = Field(default='TCP')

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, values):
        make_uppercase(values, 'protocol')
        return values

class PortConfig(BaseModel):
    port: int
    protocol: str = Field(default='TCP')

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, values):
        make_uppercase(values, 'protocol')
        return values

class IPAddressConfig(BaseModel):
    ip: str
    ports: list[str]

class RatholeRouteConfig(BaseModel):
    port: str
    host: str | None = None
    direct: bool = Field(default=False)
    virtual_path: str | None = None
    virtual_dest: str | None = None
    max_body_size: str | None = None
    connection_timeout: str | None = None

    @model_validator(mode="after")
    def validate_type(self):
        if not self.direct:
            if self.host is None:
                raise ValueError("host must be supplied when route is not direct") 
        return self

class NetworkingSpec(BaseModel):
    dependencies: list[NetworkingDependency] | None = None
    ingresses: list[IngressConfig] | None = None
    rathole_routes: list[RatholeRouteConfig] | None = None
    ip_addresses: list[IPAddressConfig] | None = None
    ports: dict[str, int | PortConfig] | None = None

class ComponentNetworking(BaseModel):
    ingress: IngressConfig | None = None

class SecurityCapSpec(BaseModel):
    add: list[str] | None = None

class SecurityGroupsSpec(BaseModel):
    add: list[int] | None = None

class SecuritySpec(BaseModel):
    cap: SecurityCapSpec | None = None
    sysctls: list[str] | None = None
    groups: SecurityGroupsSpec | None = None

class ChownStartupTask(BaseModel):
    path: str | None = None
    paths: list[str] | None = None
    owner: str
    recursive: bool = Field(default=False)

class ChmodStartupTask(BaseModel):
    path: str | None = None
    paths: list[str] | None = None
    mode: str
    recursive: bool = Field(default=False)

class ChgrpStartupTask(BaseModel):
    path: str | None = None
    paths: list[str] | None = None
    group: str | int
    recursive: bool = Field(default=False)

class GomplateInput(BaseModel):
    file: str | None = None
    files: list[str] | None = None
    dir: str | None = None
    exclude: str | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.file,
            self.files,
            self.dir
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self

class GomplateOutput(BaseModel):
    file: str | None = None
    files: list[str] | None = None
    dir: str | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.file,
            self.files,
            self.dir
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self

class GomplateStartupTask(BaseModel):
    input: GomplateInput
    output: GomplateOutput
    extra_args: list[str] | None = None
    data_sources: dict[str, str] = Field(default_factory=lambda: {})

class BusyBoxStartupTask(BaseModel):
    script: str

class StartupTask(BaseModel):
    chown: ChownStartupTask | None = None
    chmod: ChmodStartupTask | None = None
    chgrp: ChgrpStartupTask | None = None
    gomplate: GomplateStartupTask | None = None
    busybox: BusyBoxStartupTask | None = None

    @model_validator(mode="after")
    def validate_type(self):
        selected = [i for i in [
            self.chown,
            self.chmod,
            self.chgrp,
            self.gomplate,
            self.busybox
        ] if i is not None]

        if len(selected) != 1:
            raise ValueError(f"Exactly one type must be configured. found {selected}")
        return self

class StartupSpec(BaseModel):
    tasks: list[StartupTask] | None = None

# Metadata can be either a string shorthand or a full object
class ComponentMetadata(BaseModel):
    component: str | None = None
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    name: str



# App metadata
class AppMetadata(BaseModel):
    annotations: dict[str, str] = {}
    labels: dict[str, str] = {}
    namespace: str
    name: str
    project: str

class AppDefaultsPVC(BaseModel):
    storage_class: str | None = None
    size: str | None = None

class AppDefaultsImages(BaseModel):
    startup_tasks_busybox: str = Field(default='busybox')
    startup_tasks_chown: str = Field(default='busybox')
    startup_tasks_chmod: str = Field(default='busybox')
    startup_tasks_chgrp: str = Field(default='busybox')
    startup_tasks_gomplate: str = Field(default='hairyhenderson/gomplate')
    charon_k8s_job: str = Field(default='haumea/charon-k8s-job')

class SecretValueRef(BaseModel):
    namespace: str
    name: str
    key: str

class ConfigMapValueRef(BaseModel):
    namespace: str
    name: str
    key: str

class CharonBackend(BaseModel):
    subpath: str | None = None

class CharonRepositoryConfig(BaseModel):
    config_map: ConfigMapValueRef | None = None
    secret: SecretValueRef | None = None
    raw: str | None = None

class CharonVolume(BaseModel):
    secret: SecretValueRef | None = None
    dest: VolumeDestination

class CharonSource(BaseModel):
    volumes: dict[str, list[str]] | None = None

class BaseCharonConfig(BaseModel):
    schedule: str | None = None
    name: str | None = None
    repository_configs: list[CharonRepositoryConfig] | None = None
    volumes: list[CharonVolume] | None = None
    source: CharonSource | None = None 
    scale_down_deployment: bool | None = None

class CharonConfig(BaseCharonConfig):
    overlays: list[str] = Field(default_factory=lambda: [])

class AppDefaultsCharon(BaseModel):
    overlays: dict[str, BaseCharonConfig] = Field(default_factory=lambda: {})

class AppDefaultsTlsHost(BaseModel):
    wildcard: bool | None = None

class AppDefaultsTlsSecretSource(BaseModel):
    mirror: str | None =  None
    create: bool | None = None

class AppDefaultsTlsSecretFromHost(BaseModel):
    host: str
    value: str | AppDefaultsTlsSecretSource

class AppDefaultsTlsSecret(AppDefaultsTlsSecretSource):
    from_host: list[AppDefaultsTlsSecretFromHost] | None = None

class AppDefaultsTls(BaseModel):
    host: str | AppDefaultsTlsHost | None = None
    secret: str | AppDefaultsTlsSecret | None = None

class AppDefaultsNetworking(BaseModel):
    tls: AppDefaultsTls | None = None

class AppDefaults(BaseModel):
    pvc: AppDefaultsPVC | None = None
    images: AppDefaultsImages = Field(default_factory=AppDefaultsImages)
    charon: AppDefaultsCharon = Field(default_factory=AppDefaultsCharon)
    networking: AppDefaultsNetworking | None = None

class AlloyLogsSpec(BaseModel):
    process: str | None = None

class AlloyObservabilitySpec(BaseModel):
    logs: AlloyLogsSpec | None = None

class ObservabilitySpec(BaseModel):
    alloy: AlloyObservabilitySpec | None = None

class Component(BaseModel):
    metadata: ComponentMetadata

    image: str
    command: list[str] | None = None
    args: list[str] | None = None
    networking: NetworkingSpec | None = None
    volumes: dict[str, VolumeSpec] | None = None
    environment: list[EnvironmentSpec] | None = None
    security: SecuritySpec | None = None
    startup: StartupSpec | None = None
    resources: Resources | None = None
    charon: list[CharonConfig] | None = None
    observability: ObservabilitySpec | None = None
    
    # Custom fields that might be in your YAML
    class Config:
        extra = "allow"  # Allow extra fields like x-tl

# Root app definition
class AppDefinition(BaseModel):
    metadata: AppMetadata
    components: dict[str, Component]
    defaults: AppDefaults = Field(default_factory=AppDefaults)


def validate_app_yaml(app_yaml: dict) -> AppDefinition:
    return AppDefinition.model_validate(app_yaml)

