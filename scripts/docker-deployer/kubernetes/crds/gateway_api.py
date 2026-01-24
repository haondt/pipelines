from pydantic import BaseModel, Field, PlainSerializer
from typing import Annotated 
from kubernetes import client
from . import _apiClient

ObjectMeta = Annotated[client.V1ObjectMeta, PlainSerializer(_apiClient.sanitize_for_serialization)]

def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])

class CamelModel(BaseModel):
    model_config = {
        'alias_generator': to_camel,
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }

    def dump_for_dd(self):
        return self.model_dump(by_alias=True, exclude_none=True)



class ParentReference(CamelModel):
    group: str = Field(default="gateway.networking.k8s.io")
    kind: str = Field(default="Gateway")
    namespace: str | None = None
    name: str
    section_name: str | None = None
    port: int | None = None

# this class is incomplete
class HttpBackendRef(CamelModel):
    group: str | None = None
    kind: str = Field(default="Service")
    namespace: str | None = None
    name: str
    port: int | None = None # port of the service, not the target
    weight: int | None = None
    
# this class is incomplete
class HttpRouteRule(CamelModel):
    name: str | None = None
    backend_refs: list[HttpBackendRef] | None = None


class HttpRouteSpec(CamelModel):
    parent_refs: list[ParentReference] = Field(default_factory=list)
    hostnames: list[str] = Field(default_factory=list)
    rules: list[HttpRouteRule] = Field(default_factory=list)

class HttpRoute(CamelModel):
    api_version: str = Field(default='gateway.networking.k8s.io/v1')
    kind: str = Field(default='HTTPRoute')
    metadata: ObjectMeta = Field(default_factory=client.V1ObjectMeta)
    spec: HttpRouteSpec = Field(default_factory=HttpRouteSpec)
