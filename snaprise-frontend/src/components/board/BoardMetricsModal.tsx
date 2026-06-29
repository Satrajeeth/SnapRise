"use client";

import { useEffect, useState } from "react";
import { boardApi } from "@/lib/api/boards";
import type { BoardMetrics } from "@/types/api/board.types";
import { Modal } from "@/components/ui/Modal";
import { Loader2 } from "lucide-react";

interface Props {
  token: string;
  boardId: string;
  boardName: string;
  onClose: () => void;
}

export function BoardMetricsModal({ token, boardId, boardName, onClose }: Props) {
  const [metrics, setMetrics] = useState<BoardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    boardApi
      .getBoardMetrics(token, boardId)
      .then(setMetrics)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load metrics"))
      .finally(() => setLoading(false));
  }, [token, boardId]);

  const dist = metrics ? Object.entries(metrics.column_distribution) : [];
  const max = dist.reduce((m, [, v]) => Math.max(m, v), 0) || 1;

  return (
    <Modal open onClose={onClose} title="Board metrics" subtitle={`${boardName} overview`}>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-7 w-7 animate-spin text-foreground/50" />
        </div>
      ) : error ? (
        <div className="px-6 py-8 text-center text-sm text-red-500">{error}</div>
      ) : metrics ? (
        <div className="space-y-5 px-6 py-5">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-input p-4">
              <p className="text-3xl font-bold">{metrics.total_tasks}</p>
              <p className="text-xs font-medium text-foreground/50">Total tasks</p>
            </div>
            <div className="rounded-2xl bg-purple-50 p-4">
              <p className="text-3xl font-bold text-[#9333EA]">
                {Math.round(metrics.subtask_progress_percentage)}%
              </p>
              <p className="text-xs font-medium text-foreground/50">Subtasks done</p>
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-[11px] font-semibold tracking-wide text-foreground/40">
              COLUMN DISTRIBUTION
            </p>
            {dist.length === 0 && (
              <p className="text-sm text-foreground/40">No columns yet.</p>
            )}
            {dist.map(([name, count]) => (
              <div key={name} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{name}</span>
                  <span className="font-semibold text-foreground/60">{count}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-foreground/10">
                  <div
                    className="h-full rounded-full bg-[#9333EA]"
                    style={{ width: `${Math.max(6, (count / max) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
