"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { boardApi } from "@/lib/api/boards";
import { Board } from "@/types/board";
import { BoardCard } from "@/components/board/BoardCard";
import { BoardSettingsModal } from "@/components/board/BoardSettingsModal";
import { SaveAsTemplateModal } from "@/components/board/SaveAsTemplateModal";
import { TemplatesModal } from "@/components/board/TemplatesModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Plus, Loader2, LayoutGrid, LayoutTemplate } from "lucide-react";

export default function Dashboard() {
  const { token, user, logout, isLoading } = useAuth();
  const router = useRouter();
  const [boards, setBoards] = useState<Board[]>([]);
  const [loadingBoards, setLoadingBoards] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");

  const [settingsBoard, setSettingsBoard] = useState<Board | null>(null);
  const [templateBoard, setTemplateBoard] = useState<Board | null>(null);
  const [deleteBoard, setDeleteBoard] = useState<Board | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);

  useEffect(() => {
    if (!isLoading && !token) router.push("/login");
  }, [token, isLoading, router]);

  useEffect(() => {
    const fetchBoards = async () => {
      if (token) {
        try {
          setBoards(await boardApi.getBoards(token));
        } catch (error) {
          console.error("Failed to fetch boards", error);
        } finally {
          setLoadingBoards(false);
        }
      }
    };
    fetchBoards();
  }, [token]);

  const handleCreateBoard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoardName.trim() || !token) return;
    try {
      setIsCreating(true);
      const newBoard = await boardApi.createBoard(token, newBoardName);
      setBoards([...boards, newBoard]);
      setNewBoardName("");
    } catch (error) {
      console.error("Failed to create board", error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSaveTemplate = async (b: Board) => {
    if (!token) return;
    try {
      const full = await boardApi.getBoard(token, b.id);
      setTemplateBoard(full);
    } catch (error) {
      console.error("Failed to load board for template", error);
    }
  };

  const confirmDelete = async () => {
    if (!token || !deleteBoard) return;
    setDeleting(true);
    try {
      await boardApi.deleteBoard(token, deleteBoard.id);
      setBoards((prev) => prev.filter((b) => b.id !== deleteBoard.id));
    } catch (error) {
      console.error("Failed to delete board", error);
    } finally {
      setDeleting(false);
      setDeleteBoard(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-10 w-10 animate-spin text-foreground/70" />
      </div>
    );
  }

  if (!token) return null;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-background/80 px-6 py-4 backdrop-blur-md sm:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-foreground text-background">
            <LayoutGrid className="h-5 w-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">SnapRise Boards</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden text-sm text-foreground/60 sm:inline">{user?.email}</span>
          <Button variant="outline" onClick={logout}>
            Logout
          </Button>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6 sm:p-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">Your Boards</h2>
              <p className="mt-1 text-sm text-foreground/50">
                {boards.length > 0
                  ? `${boards.length} board${boards.length === 1 ? "" : "s"} · pick up where you left off`
                  : "Spin up a board and start organizing."}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowTemplates(true)}
                className="flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground/70 transition-colors hover:text-foreground"
              >
                <LayoutTemplate className="h-4 w-4" />
                <span className="hidden sm:inline">From template</span>
              </button>
              <form
                onSubmit={handleCreateBoard}
                className="flex items-center gap-2 rounded-2xl border border-border bg-card p-1.5 pl-4 transition-colors focus-within:border-foreground/30"
              >
                <input
                  type="text"
                  placeholder="New board name..."
                  value={newBoardName}
                  onChange={(e) => setNewBoardName(e.target.value)}
                  className="w-44 bg-transparent text-sm placeholder:text-foreground/40 transition-all focus:w-56 focus:outline-none"
                />
                <Button type="submit" disabled={isCreating || !newBoardName.trim()}>
                  {isCreating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="mr-2 h-4 w-4" />
                  )}
                  {isCreating ? "Creating" : "Create"}
                </Button>
              </form>
            </div>
          </div>

          {loadingBoards ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-foreground/60" />
            </div>
          ) : boards.length === 0 ? (
            <div className="animate-rise rounded-2xl border border-border bg-card py-20 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-foreground text-background">
                <LayoutGrid className="h-7 w-7" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">No boards yet</h3>
              <p className="text-foreground/50">Create your first board to get started.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {boards.map((board, i) => (
                <BoardCard
                  key={board.id}
                  board={board}
                  index={i}
                  onSettings={setSettingsBoard}
                  onSaveTemplate={handleSaveTemplate}
                  onDelete={setDeleteBoard}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* ---- Modals ---- */}
      {showTemplates && token && (
        <TemplatesModal
          token={token}
          onClose={() => setShowTemplates(false)}
          onCreated={(b) => setBoards((prev) => [...prev, b])}
        />
      )}

      {settingsBoard && token && (
        <BoardSettingsModal
          token={token}
          board={settingsBoard}
          onClose={() => setSettingsBoard(null)}
          onUpdated={(b) =>
            setBoards((prev) => prev.map((x) => (x.id === b.id ? { ...x, ...b } : x)))
          }
          onDeleted={() => {
            setBoards((prev) => prev.filter((x) => x.id !== settingsBoard.id));
            setSettingsBoard(null);
          }}
        />
      )}

      {templateBoard && token && (
        <SaveAsTemplateModal
          token={token}
          board={templateBoard}
          onClose={() => setTemplateBoard(null)}
        />
      )}

      <ConfirmDialog
        open={!!deleteBoard}
        onClose={() => setDeleteBoard(null)}
        onConfirm={confirmDelete}
        loading={deleting}
        danger
        title="Delete this board?"
        message={`"${deleteBoard?.name}" and all of its columns and tasks will be permanently removed. This action can't be undone.`}
        confirmLabel="Delete board"
      />
    </div>
  );
}
