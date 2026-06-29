"use client";

import { useCallback, useEffect, useState } from "react";
import { boardApi } from "@/lib/api/boards";
import { Modal } from "@/components/ui/Modal";
import { Loader2, Sparkles, RefreshCw } from "lucide-react";

interface Props {
  token: string;
  boardId: string;
  onClose: () => void;
}

export function SmartSortModal({ token, boardId, onClose }: Props) {
  const [suggestions, setSuggestions] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await boardApi.smartSortBoard(token, boardId);
      setSuggestions(r.suggestions ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Smart Sort failed");
    } finally {
      setLoading(false);
    }
  }, [token, boardId]);

  useEffect(() => {
    run();
  }, [run]);

  const lines = suggestions
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  return (
    <Modal
      open
      onClose={onClose}
      title="Smart Sort"
      subtitle="AI-suggested improvements & reordering"
      footer={
        <>
          <div className="flex-1" />
          <button
            onClick={run}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground/70 hover:text-foreground disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Re-run
          </button>
          <button
            onClick={onClose}
            className="rounded-xl bg-foreground px-5 py-2.5 text-sm font-medium text-background"
          >
            Done
          </button>
        </>
      }
    >
      <div className="px-6 py-5">
        {loading ? (
          <div className="flex flex-col items-center gap-3 py-12 text-foreground/50">
            <Loader2 className="h-7 w-7 animate-spin" />
            <p className="text-sm">Analyzing the board…</p>
          </div>
        ) : error ? (
          <div className="py-8 text-center text-sm text-red-500">{error}</div>
        ) : lines.length === 0 ? (
          <p className="py-8 text-center text-sm text-foreground/40">
            No suggestions returned.
          </p>
        ) : (
          <div className="space-y-2.5 rounded-2xl bg-purple-50 p-4">
            <div className="flex items-center gap-2 text-[#9333EA]">
              <Sparkles className="h-4 w-4" />
              <span className="text-[11px] font-semibold tracking-wide">SUGGESTIONS</span>
            </div>
            {lines.map((l, i) => (
              <p key={i} className="text-[13px] leading-relaxed text-foreground/75">
                {l}
              </p>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
