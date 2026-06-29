"use client";

import { useCallback, useEffect, useState, use } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { boardApi } from "@/lib/api/boards";
import { Board } from "@/types/board";
import { DragDropContext, DropResult } from "@hello-pangea/dnd";
import { KanbanColumn } from "@/components/board/KanbanColumn";
import { TaskModal } from "@/components/board/TaskModal";
import { BoardSettingsModal } from "@/components/board/BoardSettingsModal";
import { MembersModal } from "@/components/board/MembersModal";
import { BoardMetricsModal } from "@/components/board/BoardMetricsModal";
import { SmartSortModal } from "@/components/board/SmartSortModal";
import { SaveAsTemplateModal } from "@/components/board/SaveAsTemplateModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  ArrowLeft,
  Plus,
  Loader2,
  Users,
  BarChart3,
  Sparkles,
  Bookmark,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

type ActiveModal = "members" | "metrics" | "smartsort" | "template" | "settings" | null;

export default function BoardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { token, user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [board, setBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAddingColumn, setIsAddingColumn] = useState(false);
  const [newColumnName, setNewColumnName] = useState("");

  const [openTaskId, setOpenTaskId] = useState<string | null>(null);
  const [activeModal, setActiveModal] = useState<ActiveModal>(null);
  const [pendingDeleteColumn, setPendingDeleteColumn] = useState<string | null>(null);
  const [deletingColumn, setDeletingColumn] = useState(false);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [token, authLoading, router]);

  const fetchBoard = useCallback(async () => {
    if (!token) return;
    try {
      const data = await boardApi.getBoard(token, id);
      setBoard(data);
    } catch (error) {
      console.error("Failed to fetch board", error);
    } finally {
      setLoading(false);
    }
  }, [token, id]);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  const handleDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result;
    if (!destination || !board) return;
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    )
      return;

    const newBoard = { ...board };
    const sourceCol = newBoard.columns?.find((c) => c.id === source.droppableId);
    const destCol = newBoard.columns?.find((c) => c.id === destination.droppableId);
    if (!sourceCol || !destCol) return;

    const sourceTasks = [...(sourceCol.tasks || [])];
    const destTasks =
      source.droppableId === destination.droppableId
        ? sourceTasks
        : [...(destCol.tasks || [])];
    const [movedTask] = sourceTasks.splice(source.index, 1);
    movedTask.column_id = destination.droppableId;
    destTasks.splice(destination.index, 0, movedTask);

    if (source.droppableId === destination.droppableId) {
      sourceCol.tasks = destTasks;
    } else {
      sourceCol.tasks = sourceTasks;
      destCol.tasks = destTasks;
    }
    setBoard(newBoard);

    try {
      if (token)
        await boardApi.updateTask(token, draggableId, {
          column_id: destination.droppableId,
          position: destination.index,
        });
    } catch (error) {
      console.error("Failed to update task column", error);
      fetchBoard();
    }
  };

  const handleAddColumn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColumnName.trim() || !token || !board) return;
    try {
      const newOrder = board.columns?.length || 0;
      const newCol = await boardApi.createColumn(token, board.id, newColumnName, newOrder);
      setBoard({ ...board, columns: [...(board.columns || []), { ...newCol, tasks: [] }] });
      setNewColumnName("");
      setIsAddingColumn(false);
    } catch (error) {
      console.error("Failed to create column", error);
    }
  };

  const handleAddTask = async (columnId: string, title: string) => {
    if (!token || !board) return;
    try {
      const column = board.columns?.find((c) => c.id === columnId);
      const newOrder = column?.tasks?.length || 0;
      const newTask = await boardApi.createTask(token, columnId, title, "", newOrder);
      const newBoard = { ...board };
      const targetCol = newBoard.columns?.find((c) => c.id === columnId);
      if (targetCol) {
        targetCol.tasks = [...(targetCol.tasks || []), newTask];
        setBoard(newBoard);
      }
    } catch (error) {
      console.error("Failed to create task", error);
    }
  };

  const handleRenameColumn = async (columnId: string, name: string) => {
    if (!token || !board) return;
    setBoard({
      ...board,
      columns: board.columns?.map((c) => (c.id === columnId ? { ...c, name } : c)),
    });
    try {
      await boardApi.updateColumn(token, columnId, { name });
    } catch {
      fetchBoard();
    }
  };

  const handleSetWip = async (columnId: string, wipLimit: number | null) => {
    if (!token || !board) return;
    setBoard({
      ...board,
      columns: board.columns?.map((c) =>
        c.id === columnId ? { ...c, wip_limit: wipLimit } : c
      ),
    });
    try {
      await boardApi.updateColumn(token, columnId, { wip_limit: wipLimit });
    } catch {
      fetchBoard();
    }
  };

  const confirmDeleteColumn = async () => {
    if (!token || !board || !pendingDeleteColumn) return;
    setDeletingColumn(true);
    try {
      await boardApi.deleteColumn(token, pendingDeleteColumn);
      setBoard({
        ...board,
        columns: board.columns?.filter((c) => c.id !== pendingDeleteColumn),
      });
    } catch (error) {
      console.error("Failed to delete column", error);
    } finally {
      setDeletingColumn(false);
      setPendingDeleteColumn(null);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-10 w-10 animate-spin text-foreground/70" />
      </div>
    );
  }

  if (!board) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-background">
        <h2 className="mb-4 text-2xl font-bold">Board not found</h2>
        <Link href="/dashboard">
          <Button variant="outline">Back to Dashboard</Button>
        </Link>
      </div>
    );
  }

  const allTasks =
    board.columns?.flatMap((c) =>
      (c.tasks || []).map((t) => ({ id: t.id, title: t.title, column_id: c.id }))
    ) ?? [];
  const columnRefs = board.columns?.map((c) => ({ id: c.id, name: c.name })) ?? [];

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <header className="z-10 flex shrink-0 items-center gap-3 border-b border-border bg-background/80 px-6 py-4 backdrop-blur-md">
        <Link
          href="/dashboard"
          className="rounded-xl p-2 text-foreground/60 transition-colors hover:bg-input hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold tracking-tight">{board.name}</h1>
          {board.description && (
            <p className="text-sm text-foreground/50">{board.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <HeaderAction icon={<Users className="h-4 w-4" />} label="Members" onClick={() => setActiveModal("members")} />
          <HeaderAction icon={<BarChart3 className="h-4 w-4" />} label="Metrics" onClick={() => setActiveModal("metrics")} />
          <HeaderAction icon={<Sparkles className="h-4 w-4" />} label="Smart Sort" onClick={() => setActiveModal("smartsort")} />
          <HeaderAction icon={<Bookmark className="h-4 w-4" />} label="Save as template" onClick={() => setActiveModal("template")} />
          <HeaderAction icon={<Settings className="h-4 w-4" />} label="Settings" onClick={() => setActiveModal("settings")} />
        </div>
      </header>

      <main className="custom-scrollbar flex-1 overflow-x-auto overflow-y-hidden">
        <div className="flex h-full min-w-max items-start gap-6 p-6">
          <DragDropContext onDragEnd={handleDragEnd}>
            {board.columns?.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                tasks={column.tasks || []}
                onAddTask={handleAddTask}
                onOpenTask={setOpenTaskId}
                onRename={handleRenameColumn}
                onSetWip={handleSetWip}
                onDelete={(cid) => setPendingDeleteColumn(cid)}
              />
            ))}
          </DragDropContext>

          <div className="w-80 shrink-0">
            {isAddingColumn ? (
              <form
                onSubmit={handleAddColumn}
                className="rounded-2xl border border-border bg-card p-4"
              >
                <input
                  autoFocus
                  type="text"
                  placeholder="Column name..."
                  value={newColumnName}
                  onChange={(e) => setNewColumnName(e.target.value)}
                  className="mb-3 w-full rounded-xl border border-border bg-input p-3 text-sm transition-colors focus:border-foreground/40 focus:outline-none"
                />
                <div className="flex items-center gap-2">
                  <button
                    type="submit"
                    className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90"
                  >
                    Add Column
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsAddingColumn(false)}
                    className="px-4 py-2 text-sm font-medium text-foreground/50 transition-colors hover:text-foreground"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button
                onClick={() => setIsAddingColumn(true)}
                className="flex w-full items-center gap-2 rounded-2xl border border-dashed border-border px-6 py-4 text-foreground/50 transition-all hover:border-foreground/30 hover:bg-input/50 hover:text-foreground"
              >
                <Plus className="h-5 w-5" />
                <span className="font-medium">Add another column</span>
              </button>
            )}
          </div>
        </div>
      </main>

      {/* ---- Modals ---- */}
      {openTaskId && token && (
        <TaskModal
          token={token}
          taskId={openTaskId}
          columns={columnRefs}
          allTasks={allTasks}
          onClose={() => {
            setOpenTaskId(null);
            fetchBoard();
          }}
        />
      )}

      {activeModal === "members" && token && (
        <MembersModal
          token={token}
          boardId={board.id}
          currentUserId={user?.id}
          onClose={() => setActiveModal(null)}
        />
      )}

      {activeModal === "metrics" && token && (
        <BoardMetricsModal
          token={token}
          boardId={board.id}
          boardName={board.name}
          onClose={() => setActiveModal(null)}
        />
      )}

      {activeModal === "smartsort" && token && (
        <SmartSortModal token={token} boardId={board.id} onClose={() => setActiveModal(null)} />
      )}

      {activeModal === "template" && token && (
        <SaveAsTemplateModal token={token} board={board} onClose={() => setActiveModal(null)} />
      )}

      {activeModal === "settings" && token && (
        <BoardSettingsModal
          token={token}
          board={board}
          onClose={() => setActiveModal(null)}
          onUpdated={(b) => setBoard((prev) => (prev ? { ...prev, ...b } : prev))}
          onDeleted={() => router.push("/dashboard")}
        />
      )}

      <ConfirmDialog
        open={!!pendingDeleteColumn}
        onClose={() => setPendingDeleteColumn(null)}
        onConfirm={confirmDeleteColumn}
        loading={deletingColumn}
        danger
        title="Delete this column?"
        message="The column and all of its tasks will be permanently removed. This can't be undone."
        confirmLabel="Delete column"
      />
    </div>
  );
}

function HeaderAction({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className="flex items-center gap-1.5 rounded-xl border border-transparent px-2.5 py-2 text-sm font-medium text-foreground/60 transition-colors hover:border-border hover:bg-input hover:text-foreground"
    >
      {icon}
      <span className="hidden lg:inline">{label}</span>
    </button>
  );
}
