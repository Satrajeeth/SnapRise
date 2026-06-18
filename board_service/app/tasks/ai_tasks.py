import asyncio
from uuid import UUID
from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.services.board_ops import BoardOps
from app.services.ai_service import get_ai_service
from app.models.task import Task
import logging

logger = logging.getLogger(__name__)

def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

@celery_app.task
def generate_embeddings(task_id: str):
    async def _generate():
        async with SessionLocal() as db:
            task = await BoardOps.get_task(db, UUID(task_id))
            if not task:
                return
            ai_service = get_ai_service()
            emb = await ai_service.generate_embedding_text(task.title, task.content)
            
            # Since task object from get_task is in a different session,
            # refetch it using the current SessionLocal db to update
            task_model = await db.get(Task, UUID(task_id))
            if task_model:
                metadata = task_model.ai_metadata.copy() if task_model.ai_metadata else {}
                metadata["embedding_text"] = emb
                task_model.ai_metadata = metadata
                await db.commit()
    
    _run_async(_generate())

@celery_app.task
def detect_blockers(task_id: str):
    async def _detect():
        async with SessionLocal() as db:
            task = await BoardOps.get_task(db, UUID(task_id))
            if not task:
                return
            ai_service = get_ai_service()
            subtasks = [s.title for s in task.subtasks] if hasattr(task, 'subtasks') else []
            blockers = await ai_service.detect_blockers(task.title, task.content, subtasks)
            
            task_model = await db.get(Task, UUID(task_id))
            if task_model:
                metadata = task_model.ai_metadata.copy() if task_model.ai_metadata else {}
                metadata["detected_blockers"] = blockers
                task_model.ai_metadata = metadata
                await db.commit()
            
    _run_async(_detect())
