"use client";

import { Task } from "@/types/board";
import { Draggable } from "@hello-pangea/dnd";
import { GripVertical } from "lucide-react";

interface TaskCardProps {
  task: Task;
  index: number;
}

export function TaskCard({ task, index }: TaskCardProps) {
  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          className={`group rounded-xl border border-border bg-card p-4 transition-all ${
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
              <h4 className="text-sm font-medium text-foreground">
                {task.title}
              </h4>
              {task.content && (
                <p className="mt-2 line-clamp-2 text-xs text-foreground/50">
                  {task.content}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </Draggable>
  );
}
