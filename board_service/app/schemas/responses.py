from typing import List, Optional
from uuid import UUID
from .board import Board
from .column import Column
from .task import Task
from .subtask import Subtask

class BoardDetailed(Board):
    columns: List["ColumnWithTasks"] = []

class ColumnWithTasks(Column):
    tasks: List["TaskWithSubtasks"] = []

class TaskWithSubtasks(Task):
    subtasks: List[Subtask] = []

BoardDetailed.model_rebuild()
ColumnWithTasks.model_rebuild()
TaskWithSubtasks.model_rebuild()