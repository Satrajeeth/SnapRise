from typing import Dict, Any
from app.models.task import Task

class ViewService:
    @staticmethod
    def format_task_view(task: Task, view_mode: str = "detailed") -> Dict[str, Any]:
        """Format task output based on view preference (compact vs detailed)."""
        base = {
            "id": str(task.id),
            "title": task.title,
            "position": task.position,
            "column_id": str(task.column_id)
        }
        if view_mode == "detailed":
            base.update({
                "content": task.content,
                "custom_fields": task.custom_fields,
                "ai_metadata": task.ai_metadata,
                "created_at": task.created_at.isoformat() if task.created_at else None
            })
        return base
