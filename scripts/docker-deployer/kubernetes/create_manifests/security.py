from kubernetes import client
from .models import *

def add_security_context(c: client.V1Container):
    if c.security_context is None:
        c.security_context = client.V1SecurityContext()
def configure_container_security_context(c: client.V1Container, spec: SecuritySpec | ContainerSecuritySpec):
    add_security_context(c)
    if spec.user is not None:
        c.security_context.run_as_user = spec.user
    if spec.group is not None:
        c.security_context.run_as_group = spec.group
