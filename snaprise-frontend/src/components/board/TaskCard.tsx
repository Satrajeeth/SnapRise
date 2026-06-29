"use client";

import { Task } from "@/types/board";
import { Draggable } from "@hello-pangea/dnd";
import { GripVertical, CheckSquare, Lock } from "lucide-react";

interface TaskCardProps {
  task: Task;
  index: number;
  onOpen?: (taskId: string) => void;
}

export function TaskCard({ task, index, onOpen }: TaskCardProps) {
  const subtasks = task.subtasks ?? [];
  const done = subtasks.filter((s) => s.is_completed).length;
  const encrypted = task.encryption_status === "enabled";

  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onOpen?.(task.id)}
          className={`group cursor-pointer rounded-xl border border-border bg-card p-4 transition-all ${
            snapshot.isDragging
              ? "shadow-[0_16px_40px_-12px_rgba(0,0,0,0.35)] ring-1 ring-foreground/20 dark:shadow-[0_16px_40px_-8px_rgba(0,0,0,0.8)]"
              : "shadow-sm hover:-translate-y-0.5 hover:border-foreground/20"
          }`}
        >
          <div className="flex items-start gap-2">
            <div className="mt-0.5 cursor-grab active:cursor-grabbing">
              <GripVertical className="h-4 w-4 text-foreground/20 opacity-0 transition-opacity group-hover:opacity-100" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-foreground">{task.title}</h4>
              {task.content && (
                <p className="mt-2 line-clamp-2 text-xs text-foreground/50">
                  {task.content}
                </p>
              )}
              {(subtasks.length > 0 || encrypted) && (
                <div className="mt-3 flex items-center gap-3 text-[11px] font-medium text-foreground/45">
                  {subtasks.length > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <CheckSquare className="h-3.5 w-3.5" />
                      {done}/{subtasks.length}
                    </span>
                  )}
                  {encrypted && (
                    <span className="inline-flex items-center gap-1">
                      <Lock className="h-3.5 w-3.5" />
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Draggable>
  );
}
