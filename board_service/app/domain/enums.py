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


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AccessType(str, Enum):
    READ = "read"
    WRITE = "write"

class LinkType(str, Enum):
    BLOCKS = "blocks"
    IS_BLOCKED_BY = "is_blocked_by"
    RELATES_TO = "relates_to"