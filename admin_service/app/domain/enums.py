from enum import Enum


class LeadStatus(str, Enum):
    """Lifecycle of a marketing lead inside the backoffice."""

    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"


class LeadSource(str, Enum):
    """Where a lead originated.

    ``BOARD_INVITE`` covers leads captured when a board owner invites an unknown
    email (ingested from board_service's lead_outbox). ``PROMOTION`` covers leads
    created directly in the backoffice (manual entry / marketing campaigns).
    """

    BOARD_INVITE = "board_invite"
    PROMOTION = "promotion"
