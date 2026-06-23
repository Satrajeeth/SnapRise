from uuid import UUID
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.board_ops import BoardOps

class MetricsService:
    @staticmethod
    async def get_board_metrics(db: AsyncSession, board_id: UUID) -> Dict[str, Any]:
        board = await BoardOps.get_board(db, board_id, include_details=True)
        if not board: return {}
        
        total_tasks = 0
        completed_subtasks = 0
        total_subtasks = 0
        column_counts = {}
        
        for col in getattr(board, "columns", []):
            tasks = getattr(col, "tasks", [])
            col_count = len(tasks)
            total_tasks += col_count
            column_counts[col.name] = col_count
            
            for task in tasks:
                subs = getattr(task, "subtasks", [])
                total_subtasks += len(subs)
                completed_subtasks += sum(1 for s in subs if getattr(s, "is_completed", False))
                
        progress = (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "column_distribution": column_counts,
            "subtask_progress_percentage": round(progress, 2)
        }
