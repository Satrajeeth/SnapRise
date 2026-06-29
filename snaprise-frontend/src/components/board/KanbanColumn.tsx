"use client";

import { Column, Task } from "@/types/board";
import { Droppable } from "@hello-pangea/dnd";
import { TaskCard } from "./TaskCard";
import { Plus, MoreHorizontal, Pencil, Gauge, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface KanbanColumnProps {
  column: Column;
  tasks: Task[];
  onAddTask: (columnId: string, title: string) => void;
  onOpenTask?: (taskId: string) => void;
  onRename?: (columnId: string, name: string) => void;
  onSetWip?: (columnId: string, wipLimit: number | null) => void;
  onDelete?: (columnId: string) => void;
}

export function KanbanColumn({
  column,
  tasks,
  onAddTask,
  onOpenTask,
  onRename,
  onSetWip,
  onDelete,
}: KanbanColumnProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(column.name);
  const [wipOpen, setWipOpen] = useState(false);
  const [wipDraft, setWipDraft] = useState(column.wip_limit?.toString() ?? "");
  const menuRef = useRef<HTMLDivElement>(null);

  const wip = column.wip_limit ?? null;
  const overWip = wip !== null && tasks.length >= wip;

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const handleAddTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    onAddTask(column.id, newTaskTitle);
    setNewTaskTitle("");
    setIsAdding(false);
  };

  const submitRename = (e: React.FormEvent) => {
    e.preventDefault();
    const name = nameDraft.trim();
    if (name && name !== column.name) onRename?.(column.id, name);
    setRenaming(false);
  };

  const submitWip = (e: React.FormEvent) => {
    e.preventDefault();
    const v = wipDraft.trim();
    onSetWip?.(column.id, v === "" ? null : Math.max(1, parseInt(v, 10) || 1));
    setWipOpen(false);
  };

  return (
    <div className="flex max-h-full w-80 shrink-0 flex-col rounded-2xl border border-border bg-input/60">
      <div className="relative border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          {renaming ? (
            <form onSubmit={submitRename} className="flex-1">
              <input
                autoFocus
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                onBlur={submitRename}
                className="w-full rounded-lg border border-border bg-card px-2 py-1 text-sm font-semibold focus:outline-none"
              />
            </form>
          ) : (
            <h3 className="flex items-center gap-2 font-semibold text-foreground">
              {column.name}
              <span
                className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                  overWip
                    ? "border-red-200 bg-red-50 text-red-500"
                    : "border-border bg-card text-foreground/60"
                }`}
              >
                {wip !== null ? `${tasks.length} / ${wip}` : tasks.length}
              </span>
            </h3>
          )}
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="text-foreground/40 transition-colors hover:text-foreground"
          >
            <MoreHorizontal className="h-5 w-5" />
          </button>
        </div>

        {overWip && (
          <p className="mt-1.5 text-[11px] font-medium text-amber-600">
            WIP limit reached
          </p>
        )}

        {menuOpen && (
          <div
            ref={menuRef}
            className="absolute right-3 top-12 z-20 w-52 rounded-xl border border-border bg-card p-1.5 shadow-xl"
          >
            <MenuItem
              icon={<Pencil className="h-4 w-4" />}
              label="Rename column"
              onClick={() => {
                setNameDraft(column.name);
                setRenaming(true);
                setMenuOpen(false);
              }}
            />
            <MenuItem
              icon={<Gauge className="h-4 w-4" />}
              label="Set WIP limit"
              onClick={() => {
                setWipDraft(column.wip_limit?.toString() ?? "");
                setWipOpen(true);
                setMenuOpen(false);
              }}
            />
            <div className="my-1 h-px bg-border" />
            <MenuItem
              icon={<Trash2 className="h-4 w-4" />}
              label="Delete column"
              danger
              onClick={() => {
                onDelete?.(column.id);
                setMenuOpen(false);
              }}
            />
          </div>
        )}

        {wipOpen && (
          <form
            onSubmit={submitWip}
            className="absolute right-3 top-12 z-20 w-56 space-y-2.5 rounded-xl border border-border bg-card p-3 shadow-xl"
          >
            <p className="text-sm font-semibold">Set WIP limit</p>
            <input
              autoFocus
              type="number"
              min={1}
              value={wipDraft}
              onChange={(e) => setWipDraft(e.target.value)}
              placeholder="No limit"
              className="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm focus:outline-none"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setWipDraft("");
                  onSetWip?.(column.id, null);
                  setWipOpen(false);
                }}
                className="flex-1 rounded-lg border border-border py-1.5 text-sm font-medium text-foreground/60 hover:text-foreground"
              >
                Clear
              </button>
              <button
                type="submit"
                className="flex-1 rounded-lg bg-foreground py-1.5 text-sm font-medium text-background"
              >
                Save
              </button>
            </div>
          </form>
        )}
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
                <TaskCard key={task.id} task={task} index={index} onOpen={onOpenTask} />
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

function MenuItem({
  icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-input ${
        danger ? "text-red-500" : "text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
