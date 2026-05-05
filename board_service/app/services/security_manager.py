import logging
from typing import Any, Dict, Optional, Union

from app.core.security import EncryptionService, get_encryption_service
from app.domain.enums import EncryptionStatus
from app.models.board import Board
from app.models.column import Column
from app.models.task import Task

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, encryption_service: EncryptionService = None):
        self.encryption_service = encryption_service or get_encryption_service()

    def process_board_for_storage(self, board: Board) -> None:
        """Encrypt sensitive board fields before saving to DB if encryption is enabled."""
        if board.encryption_status == EncryptionStatus.ENABLED:
            if board.name and not board.name.startswith("base64:"):
                board.name = f"base64:{self.encryption_service.encrypt(board.name)}"
            if board.description and not board.description.startswith("base64:"):
                board.description = f"base64:{self.encryption_service.encrypt(board.description)}"

    def process_board_after_load(self, board: Board) -> None:
        """Decrypt sensitive board fields after loading from DB if encryption is enabled."""
        if board.encryption_status == EncryptionStatus.ENABLED:
            if board.name and board.name.startswith("base64:"):
                board.name = self.encryption_service.decrypt(board.name[7:])
            if board.description and board.description.startswith("base64:"):
                board.description = self.encryption_service.decrypt(board.description[7:])

    
    def process_task_for_storage(self, task:Task, board_encryption_status: EncryptionStatus = None) -> None:
        """Encrypt sensitive task fields before saving to DB."""
        #Task can have its own status or inherit from board
        status = task.encryption_status 
        if status == EncryptionStatus.DISABLED and board_encryption_status == EncryptionStatus.ENABLED:
            status = EncryptionStatus.ENABLED

        if status == EncryptionStatus.ENABLED:
            if task.title and not task.title.startswith("base64:"):
                task.title = f"base64:{self.encryption_service.encrypt(task.title)}"
            if task.content and not task.content.startswith("base64:"):
                task.content = f"base64:{self.encryption_service.encrypt(task.content)}"

    def process_task_after_load(self, task: Task, board_encryption_status: EncryptionStatus = None) -> None:
        """Decrypt sensitive task fields after loading from DB."""
        status = task.encryption_status 
        if status == EncryptionStatus.DISABLED and board_encryption_status == EncryptionStatus.ENABLED:
            status = EncryptionStatus.ENABLED

        if status == EncryptionStatus.ENABLED:
            if task.title and task.title.startswith("base64:"):
                task.title = self.encryption_service.decrypt(task.title[7:])
            if task.content and task.content.startswith("base64:"):
                task.content = self.encryption_service.decrypt(task.content[7:])

    def can_ai_process(self, entity: Union[Board, Column, Task]) -> bool:
         """
        Check if AI has permission to process the given entity.
        Looks for 'allow_ai' flag in ai_metadata. Defaults to True if not set.
        Hierarchical: if parent (Board/Column) denies, it's denied for children too.
        """
         # 1. Check current enitity
         if entity.ai_metadata and not entity.ai_metadata.get("allow_ai", True):
             return False
         
         # 2. Check parents
         if isinstance(entity, Task):
             # Check Column
             if entity.column :
                 if not self.can_ai_process(entity.column):
                     return False
         elif isinstance(entity, Column):
                # Check Board
             if entity.board:
                 if not self.can_ai_process(entity.board):
                     return False
                 
         return True
    
def get_security_manager() -> SecurityManager:
    return SecurityManager()