"use client";

import { useState } from "react";
import { boardApi } from "@/lib/api/boards";
import type { Board } from "@/types/board";
import type { ColumnTemplatePayload } from "@/types/api/board.types";
import { Modal } from "@/components/ui/Modal";
import { Loader2, Check } from "lucide-react";

interface Props {
  token: string;
  board: Board;
  onClose: () => void;
  onSaved?: () => void;
}

export function SaveAsTemplateModal({ token, board, onClose, onSaved }: Props) {
  const [name, setName] = useState(`${board.name} template`);
  const [description, setDescription] = useState(board.description ?? "");
  const [isPublic, setIsPublic] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const columns: ColumnTemplatePayload[] = (board.columns ?? [])
        .slice()
        .sort((a, b) => a.position - b.position)
        .map((c, i) => ({
          name: c.name,
          position: i,
          wip_limit: c.wip_limit ?? null,
        }));
      await boardApi.createTemplate(token, {
        name: name.trim(),
        description: description.trim() || null,
        is_public: isPublic,
        payload: { columns },
      });
      onSaved?.();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save template");
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Save as template"
      subtitle="Reuse this board's columns and setup"
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
            Save template
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
          <label className="text-xs font-medium text-foreground/50">Template name</label>
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
            rows={2}
            className="w-full resize-none rounded-xl border border-border bg-input px-3.5 py-3 text-sm text-foreground/80 focus:border-foreground/40 focus:outline-none"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground/50">Visibility</label>
          <div className="grid grid-cols-2 gap-2.5">
            <VisCard
              title="Private"
              sub="Only you"
              selected={!isPublic}
              onClick={() => setIsPublic(false)}
            />
            <VisCard
              title="Public"
              sub="Anyone can use"
              selected={isPublic}
              onClick={() => setIsPublic(true)}
            />
          </div>
        </div>
        <p className="text-[11px] text-foreground/40">
          Captures {board.columns?.length ?? 0} column
          {(board.columns?.length ?? 0) === 1 ? "" : "s"}. Tasks are not copied.
        </p>
      </div>
    </Modal>
  );
}

function VisCard({
  title,
  sub,
  selected,
  onClick,
}: {
  title: string;
  sub: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl border p-3.5 text-left transition-colors ${
        selected
          ? "border-[#9333EA] bg-purple-50"
          : "border-border bg-input hover:border-foreground/20"
      }`}
    >
      <div className="flex items-center justify-between">
        <span
          className={`text-sm font-semibold ${selected ? "text-[#9333EA]" : "text-foreground"}`}
        >
          {title}
        </span>
        <span
          className={`flex h-4 w-4 items-center justify-center rounded-full border ${
            selected ? "border-[#9333EA] bg-[#9333EA] text-white" : "border-foreground/30"
          }`}
        >
          {selected && <Check className="h-3 w-3" />}
        </span>
      </div>
      <p className="mt-1 text-xs text-foreground/50">{sub}</p>
    </button>
  );
}
