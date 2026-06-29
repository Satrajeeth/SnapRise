"use client";

import { useEffect, useState } from "react";
import { boardApi } from "@/lib/api/boards";
import type { BoardMemberResponse, BoardRole } from "@/types/api/board.types";
import { Modal } from "@/components/ui/Modal";
import { Loader2, UserPlus, X } from "lucide-react";

const ROLES: BoardRole[] = ["owner", "editor", "viewer"];

interface Props {
  token: string;
  boardId: string;
  currentUserId?: string;
  onClose: () => void;
}

export function MembersModal({ token, boardId, currentUserId, onClose }: Props) {
  const [members, setMembers] = useState<BoardMemberResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<BoardRole>("editor");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setMembers(await boardApi.getBoardMembers(token, boardId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load members");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await boardApi.addBoardMember(token, boardId, userId.trim(), role);
      setUserId("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add member");
    } finally {
      setAdding(false);
    }
  };

  const changeRole = async (m: BoardMemberResponse, newRole: BoardRole) => {
    setMembers((prev) =>
      prev.map((x) => (x.id === m.id ? { ...x, role: newRole } : x))
    );
    try {
      await boardApi.updateBoardMember(token, boardId, m.user_id, newRole);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update role");
      load();
    }
  };

  const remove = async (m: BoardMemberResponse) => {
    setMembers((prev) => prev.filter((x) => x.id !== m.id));
    try {
      await boardApi.removeBoardMember(token, boardId, m.user_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove member");
      load();
    }
  };

  return (
    <Modal open onClose={onClose} title="Members" subtitle="Manage who can access this board">
      <div className="px-6 pb-4">
        <form onSubmit={handleAdd} className="flex items-center gap-2">
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="User ID (UUID)"
            className="flex-1 rounded-xl border border-border bg-input px-3.5 py-2.5 text-sm focus:border-foreground/40 focus:outline-none"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as BoardRole)}
            className="rounded-xl border border-border bg-input px-3 py-2.5 text-sm capitalize focus:outline-none"
          >
            {ROLES.filter((r) => r !== "owner").map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={adding || !userId.trim()}
            className="flex items-center gap-1.5 rounded-xl bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
            Add
          </button>
        </form>
        <p className="mt-2 text-[11px] text-foreground/40">
          Invites use a user&apos;s ID. Email-based invites need a lookup endpoint on the
          auth service (see notes).
        </p>
        {error && (
          <div className="mt-3 rounded-lg border border-red-100 bg-red-50 p-2.5 text-center text-sm text-red-500">
            {error}
          </div>
        )}
      </div>

      <div className="h-px w-full bg-border" />

      <div className="px-3 py-2">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-foreground/50" />
          </div>
        ) : (
          members.map((m) => {
            const isSelf = currentUserId && m.user_id === currentUserId;
            const initials = m.user_id.replace(/[^a-zA-Z0-9]/g, "").slice(0, 2).toUpperCase();
            return (
              <div key={m.id} className="flex items-center gap-3 px-3 py-2.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-purple-100 text-xs font-semibold text-[#9333EA]">
                  {initials || "?"}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-semibold">
                      {m.user_id.slice(0, 8)}…
                    </span>
                    {isSelf && (
                      <span className="rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold text-[#9333EA]">
                        You
                      </span>
                    )}
                  </div>
                  <p className="truncate text-xs text-foreground/50">{m.user_id}</p>
                </div>
                {m.role === "owner" ? (
                  <span className="rounded-lg bg-input px-3 py-2 text-xs font-medium text-foreground/60">
                    Owner
                  </span>
                ) : (
                  <>
                    <select
                      value={m.role}
                      onChange={(e) => changeRole(m, e.target.value as BoardRole)}
                      className="rounded-lg border border-border bg-input px-2.5 py-1.5 text-xs capitalize focus:outline-none"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => remove(m)}
                      className="text-foreground/30 transition-colors hover:text-red-500"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </>
                )}
              </div>
            );
          })
        )}
        {!loading && members.length === 0 && (
          <p className="px-3 py-6 text-center text-sm text-foreground/40">
            No members yet.
          </p>
        )}
      </div>
    </Modal>
  );
}
