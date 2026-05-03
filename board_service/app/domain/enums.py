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
