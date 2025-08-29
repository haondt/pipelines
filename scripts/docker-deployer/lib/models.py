from enum import Enum
from dataclasses import dataclass, field

class StatusEnum(Enum):
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"

class ProjectTypeEnum(Enum):
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    UNKNOWN = "unknown"

@dataclass
class ServiceDiff:
    status: StatusEnum = field(default=StatusEnum.UNCHANGED)

@dataclass
class ProjectDiff:
    services: dict[str, ServiceDiff] = field(default_factory=dict)
    status: StatusEnum = field(default=StatusEnum.UNCHANGED)
    type: ProjectTypeEnum = field(default=ProjectTypeEnum.UNKNOWN)

@dataclass
class RepoDiff:
    projects: dict[str, ProjectDiff] = field(default_factory=dict)

