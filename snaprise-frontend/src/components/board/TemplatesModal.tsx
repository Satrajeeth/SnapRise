"use client";

import { useEffect, useState } from "react";
import { boardApi } from "@/lib/api/boards";
import type { Board, BoardTemplate } from "@/types/api/board.types";
import { Modal } from "@/components/ui/Modal";
import { Loader2, LayoutGrid, Check, Globe, Lock } from "lucide-react";

interface Props {
  token: string;
  onClose: () => void;
  onCreated: (board: Board) => void;
}

export function TemplatesModal({ token, onClose, onCreated }: Props) {
  const [templates, setTemplates] = useState<BoardTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<BoardTemplate | null>(null);
  const [boardName, setBoardName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    boardApi
      .getTemplates(token)
      .then(setTemplates)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load templates"))
      .finally(() => setLoading(false));
  }, [token]);

  const pick = (t: BoardTemplate) => {
    setSelected(t);
    setBoardName(t.name);
  };

  const handleCreate = async () => {
    if (!selected || !boardName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const board = await boardApi.createBoardFromTemplate(
        token,
        selected.id,
        boardName.trim()
      );
      onCreated(board);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create board");
      setCreating(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      size="xl"
      title="New board from template"
      subtitle="Start faster with a prebuilt column setup"
      footer={
        selected ? (
          <>
            <input
              value={boardName}
              onChange={(e) => setBoardName(e.target.value)}
              placeholder="New board name…"
              className="flex-1 rounded-xl border border-border bg-input px-3.5 py-2.5 text-sm focus:border-foreground/40 focus:outline-none"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !boardName.trim()}
              className="flex items-center gap-2 rounded-xl bg-[#9333EA] px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              Create board
            </button>
          </>
        ) : (
          <p className="py-1 text-sm text-foreground/40">Select a template to continue.</p>
        )
      }
    >
      <div className="px-6 py-5">
        {error && (
          <div className="mb-4 rounded-lg border border-red-100 bg-red-50 p-2.5 text-center text-sm text-red-500">
            {error}
          </div>
        )}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-7 w-7 animate-spin text-foreground/50" />
          </div>
        ) : templates.length === 0 ? (
          <p className="py-12 text-center text-sm text-foreground/40">
            No templates yet. Save a board as a template to reuse it here.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {templates.map((t) => {
              const isSel = selected?.id === t.id;
              const cols = t.payload?.columns?.length ?? 0;
              return (
                <button
                  key={t.id}
                  onClick={() => pick(t)}
                  className={`rounded-2xl border p-4 text-left transition-all ${
                    isSel
                      ? "border-[#9333EA] bg-purple-50"
                      : "border-border bg-card hover:border-foreground/20"
                  }`}
                >
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100 text-[#9333EA]">
                      <LayoutGrid className="h-5 w-5" />
                    </div>
                    {isSel && (
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#9333EA] text-white">
                        <Check className="h-3.5 w-3.5" />
                      </span>
                    )}
                  </div>
                  <h3 className="text-[15px] font-semibold">{t.name}</h3>
                  {t.description && (
                    <p className="mt-1 line-clamp-2 text-sm text-foreground/50">
                      {t.description}
                    </p>
                  )}
                  <div className="mt-3 flex items-center gap-3 text-xs font-medium text-foreground/40">
                    <span>{cols} columns</span>
                    <span className="inline-flex items-center gap-1">
                      {t.is_public ? (
                        <>
                          <Globe className="h-3.5 w-3.5" /> Public
                        </>
                      ) : (
                        <>
                          <Lock className="h-3.5 w-3.5" /> Private
                        </>
                      )}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </Modal>
  );
}
