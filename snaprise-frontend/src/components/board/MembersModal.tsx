"use client";

import { useEffect, useState } from "react";
import { boardApi } from "@/lib/api/boards";
import { authApi } from "@/lib/api";
import type {
  BoardMemberResponse,
  BoardRole,
  InvitationResponse,
} from "@/types/api/board.types";
import { Modal } from "@/components/ui/Modal";
import { Loader2, UserPlus, X, Mail, Clock } from "lucide-react";

const ROLES: BoardRole[] = ["owner", "editor", "viewer"];

interface Props {
  token: string;
  boardId: string;
  currentUserId?: string;
  onClose: () => void;
}

export function MembersModal({ token, boardId, currentUserId, onClose }: Props) {
  const [members, setMembers] = useState<BoardMemberResponse[]>([]);
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<BoardRole>("editor");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async () => {
    try {
      // Pending invitations sit alongside members; load both. Invitations are
      // best-effort (a viewer might lack access) so they never block members.
      const [memberList, inviteList] = await Promise.all([
        boardApi.getBoardMembers(token, boardId),
        boardApi.listInvitations(token, boardId).catch(() => [] as InvitationResponse[]),
      ]);
      setMembers(memberList);
      setInvitations(inviteList);
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
    const value = email.trim();
    if (!value) return;
    setAdding(true);
    setError(null);
    setNotice(null);
    try {
      // Branch: resolve the email to a user id. If they have an account, add
      // them straight away; if auth returns 404 (USER_NOT_FOUND), fall through
      // to creating a pending invitation instead.
      const resolved = await authApi.resolveEmail(token, value);
      await boardApi.addBoardMember(token, boardId, resolved.user_id, role);
      setNotice(`${value} added to the board.`);
      setEmail("");
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg === "USER_NOT_FOUND") {
        try {
          await boardApi.inviteMember(token, boardId, value, role);
          setNotice(`Invitation sent to ${value}.`);
          setEmail("");
          await load();
        } catch (inviteErr) {
          setError(inviteErr instanceof Error ? inviteErr.message : "Failed to send invitation");
        }
      } else {
        setError(msg || "Failed to add member");
      }
    } finally {
      setAdding(false);
    }
  };

  const revokeInvite = async (inv: InvitationResponse) => {
    setInvitations((prev) => prev.filter((x) => x.id !== inv.id));
    try {
      await boardApi.revokeInvitation(token, boardId, inv.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to revoke invitation");
      load();
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
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Invite by email"
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
            disabled={adding || !email.trim()}
            className="flex items-center gap-1.5 rounded-xl bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
            Add
          </button>
        </form>
        <p className="mt-2 text-[11px] text-foreground/40">
          Existing users are added instantly. Unknown emails get an invitation to join the board.
        </p>
        {notice && (
          <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50 p-2.5 text-center text-sm text-emerald-600">
            {notice}
          </div>
        )}
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

      {!loading && invitations.length > 0 && (
        <>
          <div className="h-px w-full bg-border" />
          <div className="px-3 py-2">
            <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-foreground/40">
              Pending invitations
            </p>
            {invitations.map((inv) => (
              <div key={inv.id} className="flex items-center gap-3 px-3 py-2.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-600">
                  <Mail className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{inv.email}</p>
                  <p className="flex items-center gap-1 text-xs text-foreground/50">
                    <Clock className="h-3 w-3" />
                    Invited as {inv.role} · expires {new Date(inv.expires_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => revokeInvite(inv)}
                  title="Revoke invitation"
                  className="text-foreground/30 transition-colors hover:text-red-500"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </Modal>
  );
}
