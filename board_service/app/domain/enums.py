from enum import Enum


class LifecycleStage(str, Enum):
    IDEA = "idea"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class EncryptionStatus(str, Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    PENDING = "pending"


class BoardRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class AccessType(str, Enum):
    READ = "read"
    WRITE = "write"
