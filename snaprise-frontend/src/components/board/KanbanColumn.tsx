"use client";

import { Column, Task } from "@/types/board";
import { Droppable } from "@hello-pangea/dnd";
import { TaskCard } from "./TaskCard";
import { Plus, MoreHorizontal } from "lucide-react";
import { useState } from "react";

interface KanbanColumnProps {
  column: Column;
  tasks: Task[];
  onAddTask: (columnId: string, title: string) => void;
}

export function KanbanColumn({ column, tasks, onAddTask }: KanbanColumnProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState("");

  const handleAddTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    onAddTask(column.id, newTaskTitle);
    setNewTaskTitle("");
    setIsAdding(false);
  };

  return (
    <div className="flex max-h-full w-80 shrink-0 flex-col rounded-2xl border border-border bg-input/60">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="flex items-center gap-2 font-semibold text-foreground">
          {column.name}
          <span className="rounded-full border border-border bg-card px-2 py-0.5 text-xs font-medium text-foreground/60">
            {tasks.length}
          </span>
        </h3>
        <button className="text-foreground/40 transition-colors hover:text-foreground">
          <MoreHorizontal className="h-5 w-5" />
        </button>
      </div>

      <div className="custom-scrollbar flex-1 overflow-y-auto p-4">
        <Droppable droppableId={column.id}>
          {(provided, snapshot) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              className={`flex min-h-[100px] flex-col gap-3 rounded-xl transition-colors ${
                snapshot.isDraggingOver ? "bg-foreground/[0.04]" : ""
              }`}
            >
              {tasks.map((task, index) => (
                <TaskCard key={task.id} task={task} index={index} />
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>

        {isAdding ? (
          <form onSubmit={handleAddTask} className="mt-3">
            <textarea
              autoFocus
              className="w-full resize-none rounded-xl border border-border bg-card p-3 text-sm shadow-sm transition-colors focus:border-foreground/40 focus:outline-none"
              placeholder="What needs to be done?"
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAddTask(e);
                } else if (e.key === "Escape") {
                  setIsAdding(false);
                }
              }}
              rows={3}
            />
            <div className="mt-2 flex items-center gap-2">
              <button
                type="submit"
                className="rounded-lg bg-foreground px-3 py-1.5 text-xs font-medium text-background transition-opacity hover:opacity-90"
              >
                Add Task
              </button>
              <button
                type="button"
                onClick={() => setIsAdding(false)}
                className="px-3 py-1.5 text-xs font-medium text-foreground/50 transition-colors hover:text-foreground"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setIsAdding(true)}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-transparent py-2 text-sm text-foreground/50 transition-colors hover:border-border hover:bg-card hover:text-foreground"
          >
            <Plus className="h-4 w-4" />
            Add Task
          </button>
        )}
      </div>
    </div>
  );
}
