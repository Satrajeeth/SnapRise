from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.task import Task
from app.models.board import Board
from app.models.column import Column
import logging

logger = logging.getLogger(__name__)

class AutomationService:
    @staticmethod
    async def process_task_move(db: AsyncSession, task: Task, old_col_id: UUID, new_col_id: UUID) -> None:
        """
        Triggered when a task moves columns. Executes any rules defined in board settings.
        Rule format: board.settings['automations'] = [
            {'trigger_column_id': 'uuid', 'action': 'set_custom_field', 'field': 'Status', 'value': 'In Progress'}
        ]
        """
        try:
            # Get board
            result = await db.execute(
                select(Board).join(Column).where(Column.id == new_col_id)
            )
            board = result.scalar_one_or_none()
            if not board or not board.settings:
                return

            automations = board.settings.get("automations", [])
            for rule in automations:
                if rule.get("trigger_column_id") == str(new_col_id):
                    action = rule.get("action")
                    if action == "set_custom_field":
                        field = rule.get("field")
                        value = rule.get("value")
                        if field and value:
                            # Must create a copy of dict to trigger SQLAlchemy JSONB mutation tracking
                            current_fields = task.custom_fields.copy() if task.custom_fields else {}
                            current_fields[field] = value
                            task.custom_fields = current_fields
                            
        except Exception as e:
            logger.error(f"Error processing automation for task {task.id}: {e}")
