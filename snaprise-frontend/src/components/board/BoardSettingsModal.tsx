"use client";

import { useState } from "react";
import { boardApi } from "@/lib/api/boards";
import type { Board, LifecycleStage } from "@/types/board";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Loader2 } from "lucide-react";

const STAGES: LifecycleStage[] = ["idea", "active", "paused", "archived"];
const STAGE_LABEL: Record<LifecycleStage, string> = {
  idea: "Idea",
  active: "Active",
  paused: "Paused",
  archived: "Archived",
};

interface Props {
  token: string;
  board: Board;
  onClose: () => void;
  onUpdated: (board: Board) => void;
  onDeleted: () => void;
}

export function BoardSettingsModal({ token, board, onClose, onUpdated, onDeleted }: Props) {
  const [name, setName] = useState(board.name);
  const [description, setDescription] = useState(board.description ?? "");
  const [stage, setStage] = useState<LifecycleStage>(board.lifecycle_stage ?? "active");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await boardApi.updateBoard(token, board.id, {
        name: name.trim(),
        description: description.trim() || null,
        lifecycle_stage: stage,
      });
      onUpdated({ ...board, ...updated });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save board");
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await boardApi.deleteBoard(token, board.id);
      onDeleted();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete board");
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  return (
    <>
      <Modal
        open
        onClose={onClose}
        title="Board settings"
        subtitle="Update details or remove this board"
        footer={
          <>
            <div className="flex-1" />
            <button
              onClick={onClose}
              className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground/70 hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="flex items-center gap-2 rounded-xl bg-[#9333EA] px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </button>
          </>
        }
      >
        <div className="space-y-4 px-6 py-4">
          {error && (
            <div className="rounded-lg border border-red-100 bg-red-50 p-2.5 text-center text-sm text-red-500">
              {error}
            </div>
          )}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground/50">Board name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-border bg-input px-3.5 py-3 text-[15px] font-medium focus:border-foreground/40 focus:outline-none"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground/50">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full resize-none rounded-xl border border-border bg-input px-3.5 py-3 text-sm text-foreground/80 focus:border-foreground/40 focus:outline-none"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground/50">Lifecycle stage</label>
            <div className="flex gap-1 rounded-xl border border-border bg-input p-1">
              {STAGES.map((s) => (
                <button
                  key={s}
                  onClick={() => setStage(s)}
                  className={`flex-1 rounded-lg py-2 text-sm font-medium transition-colors ${
                    stage === s
                      ? "bg-card text-foreground shadow-sm"
                      : "text-foreground/50 hover:text-foreground"
                  }`}
                >
                  {STAGE_LABEL[s]}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="h-px w-full bg-border" />

        <div className="flex items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-sm font-semibold text-red-500">Delete board</p>
            <p className="text-xs text-foreground/50">
              Permanently removes all columns and tasks
            </p>
          </div>
          <button
            onClick={() => setConfirmDelete(true)}
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-500 transition-colors hover:bg-red-100"
          >
            Delete
          </button>
        </div>
      </Modal>

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        loading={deleting}
        danger
        title="Delete this board?"
        message={`"${board.name}" and all of its columns and tasks will be permanently removed. This action can't be undone.`}
        confirmLabel="Delete board"
      />
    </>
  );
}
