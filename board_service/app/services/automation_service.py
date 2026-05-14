import logging
from typing import Any,Dict,List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.board import Board
from app.models.column import Column
from app.models.task import Task
from app.domain.enums import LifecycleStage

#It creates (or gets) a logger named after the current file/module so you can log messages from it.
logger = logging.getLogger(__name__)

class AutomationService:
    @staticmethod
    async def process_task_move(db: AsyncSession, task: Task, old_column_id: Any, new_column_id: Any):
        """Process automations when a task is moved between columns."""
        #1.Fetch board and columns
        from sqlalchemy import select 
        result = await db.execute(
            select(Board)
            .join(Column)
            .where(Column.id == new_column_id)
        )
        board = result.scalar_one_or_none()
        if not board:
            return
        
        new_col = await db.get(Column, new_column_id)
        if not new_col:
            return
        
        #2.Check for autoamtions in board settings
        automations = board.settings.get("automations", [])
        for auto in automations:
            if auto.get("trigger") == "move_to_column":
                target = auto.get("target_column")
                if target == new_col.name:
                    await AutomationService._execute_action(db, task, auto.get("action"))

    @staticmethod
    async def _execute_action(db: AsyncSession, task: Task, action: str):
        logger.info(f"Executing automation action '{action}' for task '{task.title}'")
        if action == "archive_task":
        # This is tricky because Task doesn't have lifecycle_stage, Board does.
        # But let's assume we use a setting or flag.
        # For now, let's just update a field in settings as an example.
            if not task.settings:
                task.settings = {}
            task.settings["archived_by_automation"] = True
        elif action == "set_completed":
            #Update all subtasks
            from app.models.subtask import Subtask
            from sqlalchemy import update
            await db.execute(
                update(Subtask)
                .where(Subtask.task_id == task.id)
                .values(is_completed=True)
            )

        # Add more actions as need 



