"use client";

import { useCallback, useEffect, useState } from "react";
import { boardApi } from "@/lib/api/boards";
import type {
  TaskDetailed,
  Subtask,
  LinkType,
  EncryptionStatus,
  AiAnalyzeResult,
} from "@/types/api/board.types";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  Loader2,
  Plus,
  Trash2,
  Sparkles,
  Check,
  Link2,
} from "lucide-react";

interface ColumnRef {
  id: string;
  name: string;
}
interface TaskRef {
  id: string;
  title: string;
  column_id: string;
}

interface TaskModalProps {
  token: string;
  taskId: string;
  columns: ColumnRef[];
  /** Every task on the board, used for the link-target picker. */
  allTasks: TaskRef[];
  onClose: () => void;
}

const LINK_LABELS: Record<LinkType, string> = {
  blocks: "Blocks",
  is_blocked_by: "Blocked by",
  relates_to: "Relates to",
};

export function TaskModal({ token, taskId, columns, allTasks, onClose }: TaskModalProps) {
  const [detail, setDetail] = useState<TaskDetailed | null>(null);
  const [loading, setLoading] = useState(true);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [columnId, setColumnId] = useState("");
  const [encryption, setEncryption] = useState<EncryptionStatus>("disabled");
  const [saving, setSaving] = useState(false);

  const [newSubtask, setNewSubtask] = useState("");
  const [linkType, setLinkType] = useState<LinkType>("blocks");
  const [linkTarget, setLinkTarget] = useState("");

  const [analysis, setAnalysis] = useState<AiAnalyzeResult | null>(null);
  const [aiNote, setAiNote] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState<"analyze" | "classify" | "suggest" | null>(null);

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const data = await boardApi.getTask(token, taskId, true);
    setDetail(data);
    return data;
  }, [token, taskId]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    boardApi
      .getTask(token, taskId, true)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        setTitle(data.title);
        setContent(data.content ?? "");
        setColumnId(data.column_id);
        setEncryption(data.encryption_status);
      })
      .catch((e) => active && setError(e.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [token, taskId]);

  const columnName = (id: string) => columns.find((c) => c.id === id)?.name ?? "—";

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await boardApi.updateTask(token, taskId, {
        title,
        content,
        column_id: columnId,
        encryption_status: encryption,
      });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save task");
      setSaving(false);
    }
  };

  const toggleSubtask = async (s: Subtask) => {
    setDetail((d) =>
      d
        ? {
            ...d,
            subtasks: d.subtasks.map((x) =>
              x.id === s.id ? { ...x, is_completed: !x.is_completed } : x
            ),
          }
        : d
    );
    try {
      await boardApi.updateSubtask(token, s.id, { is_completed: !s.is_completed });
    } catch {
      reload();
    }
  };

  const addSubtask = async () => {
    if (!newSubtask.trim()) return;
    setNewSubtask("");
    await boardApi.createSubtask(token, taskId, newSubtask.trim());
    await reload();
  };

  const deleteSubtask = async (id: string) => {
    await boardApi.deleteSubtask(token, id);
    await reload();
  };

  const addLink = async () => {
    if (!linkTarget) return;
    try {
      await boardApi.createTaskLink(token, taskId, {
        target_task_id: linkTarget,
        link_type: linkType,
      });
      setLinkTarget("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to link task");
    }
  };

  const deleteLink = async (linkId: string) => {
    await boardApi.deleteTaskLink(token, linkId);
    await reload();
  };

  const runAnalyze = async () => {
    setAiBusy("analyze");
    setAiNote(null);
    try {
      setAnalysis(await boardApi.analyzeTask(token, taskId));
    } catch (e) {
      setAiNote(e instanceof Error ? e.message : "AI analysis failed");
    } finally {
      setAiBusy(null);
    }
  };

  const runClassify = async () => {
    setAiBusy("classify");
    try {
      const r = await boardApi.classifyTask(token, taskId);
      setAiNote(`Suggested column: ${r.suggested_column}`);
    } catch (e) {
      setAiNote(e instanceof Error ? e.message : "Classification failed");
    } finally {
      setAiBusy(null);
    }
  };

  const runSuggest = async () => {
    setAiBusy("suggest");
    try {
      const r = await boardApi.suggestTaskColumn(token, taskId);
      setAiNote(`Suggested column: ${r.suggested_column}`);
    } catch (e) {
      setAiNote(e instanceof Error ? e.message : "Suggestion failed");
    } finally {
      setAiBusy(null);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await boardApi.deleteTask(token, taskId);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete task");
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  const done = detail?.subtasks.filter((s) => s.is_completed).length ?? 0;
  const total = detail?.subtasks.length ?? 0;
  const linkTargets = allTasks.filter((t) => t.id !== taskId);

  return (
    <>
      <Modal
        open
        onClose={onClose}
        size="lg"
        eyebrow="TASK"
        title={loading ? "Loading…" : title || "Untitled task"}
        subtitle={`Column · ${columnName(columnId)}`}
        footer={
          <>
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-2 rounded-xl border border-red-200 bg-card px-4 py-2.5 text-sm font-medium text-red-500 transition-colors hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4" /> Delete
            </button>
            <div className="flex-1" />
            <button
              onClick={onClose}
              className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground/70 transition-colors hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || loading}
              className="flex items-center gap-2 rounded-xl bg-[#9333EA] px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save changes
            </button>
          </>
        }
      >
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-7 w-7 animate-spin text-foreground/50" />
          </div>
        ) : (
          <div className="flex flex-col">
            {error && (
              <div className="mx-6 mt-2 rounded-lg border border-red-100 bg-red-50 p-2.5 text-center text-sm text-red-500">
                {error}
              </div>
            )}

            {/* Title + description */}
            <div className="space-y-4 px-6 py-4">
              <Field label="Title">
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-xl border border-border bg-input px-3.5 py-3 text-base font-semibold focus:border-foreground/40 focus:outline-none"
                />
              </Field>
              <Field label="Description">
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={4}
                  placeholder="Add more detail…"
                  className="w-full resize-none rounded-xl border border-border bg-input px-3.5 py-3 text-sm leading-relaxed text-foreground/80 focus:border-foreground/40 focus:outline-none"
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Column">
                  <Select value={columnId} onChange={setColumnId}>
                    {columns.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Encryption">
                  <Select
                    value={encryption}
                    onChange={(v) => setEncryption(v as EncryptionStatus)}
                  >
                    <option value="disabled">Disabled</option>
                    <option value="enabled">Enabled</option>
                  </Select>
                </Field>
              </div>
            </div>

            <Divider />

            {/* Subtasks */}
            <Section>
              <SectionHeader title="Subtasks" trailing={`${done} / ${total}`} />
              {total > 0 && (
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-foreground/10">
                  <div
                    className="h-full rounded-full bg-[#9333EA] transition-all"
                    style={{ width: `${total ? (done / total) * 100 : 0}%` }}
                  />
                </div>
              )}
              <div className="space-y-2">
                {detail?.subtasks.map((s) => (
                  <div
                    key={s.id}
                    className="group flex items-center gap-3 rounded-xl border border-border bg-input/60 px-3 py-2.5"
                  >
                    <button
                      onClick={() => toggleSubtask(s)}
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors ${
                        s.is_completed
                          ? "border-[#9333EA] bg-[#9333EA] text-white"
                          : "border-foreground/30 bg-card"
                      }`}
                    >
                      {s.is_completed && <Check className="h-3.5 w-3.5" />}
                    </button>
                    <span
                      className={`flex-1 text-sm ${
                        s.is_completed
                          ? "text-foreground/40 line-through"
                          : "text-foreground"
                      }`}
                    >
                      {s.title}
                    </span>
                    <button
                      onClick={() => deleteSubtask(s.id)}
                      className="text-foreground/30 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  addSubtask();
                }}
                className="flex items-center gap-2 rounded-xl border border-dashed border-border bg-input px-3 py-2"
              >
                <Plus className="h-4 w-4 text-[#9333EA]" />
                <input
                  value={newSubtask}
                  onChange={(e) => setNewSubtask(e.target.value)}
                  placeholder="Add a subtask…"
                  className="flex-1 bg-transparent text-sm placeholder:text-foreground/40 focus:outline-none"
                />
              </form>
            </Section>

            <Divider />

            {/* Linked tasks */}
            <Section>
              <SectionHeader title="Linked tasks" />
              <div className="space-y-2">
                {detail?.links.length === 0 && (
                  <p className="text-sm text-foreground/40">No linked tasks yet.</p>
                )}
                {detail?.links.map((l) => {
                  const counterpart = l.target_task ?? l.source_task;
                  return (
                    <div
                      key={l.id}
                      className="group flex items-center gap-3 rounded-xl border border-border bg-input/60 px-3 py-2.5"
                    >
                      <span className="shrink-0 rounded-full bg-purple-100 px-2.5 py-0.5 text-[11px] font-semibold text-[#9333EA]">
                        {LINK_LABELS[l.link_type]}
                      </span>
                      <span className="flex-1 truncate text-sm">
                        {counterpart?.title ?? "Task"}
                      </span>
                      <button
                        onClick={() => deleteLink(l.id)}
                        className="text-foreground/30 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
              {linkTargets.length > 0 && (
                <div className="flex items-center gap-2">
                  <Select value={linkType} onChange={(v) => setLinkType(v as LinkType)}>
                    <option value="blocks">Blocks</option>
                    <option value="is_blocked_by">Blocked by</option>
                    <option value="relates_to">Relates to</option>
                  </Select>
                  <Select value={linkTarget} onChange={setLinkTarget} className="flex-1">
                    <option value="">Select a task…</option>
                    {linkTargets.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.title}
                      </option>
                    ))}
                  </Select>
                  <button
                    onClick={addLink}
                    disabled={!linkTarget}
                    className="flex items-center gap-1.5 rounded-xl bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-40"
                  >
                    <Link2 className="h-4 w-4" /> Link
                  </button>
                </div>
              )}
            </Section>

            <Divider />

            {/* AI assist */}
            <Section>
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-[#9333EA]" />
                <h3 className="text-sm font-semibold">AI Assist</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <AiButton onClick={runAnalyze} busy={aiBusy === "analyze"}>
                  Analyze
                </AiButton>
                <AiButton onClick={runClassify} busy={aiBusy === "classify"}>
                  Classify
                </AiButton>
                <AiButton onClick={runSuggest} busy={aiBusy === "suggest"}>
                  Suggest column
                </AiButton>
              </div>
              {(analysis || aiNote) && (
                <div className="space-y-2 rounded-xl bg-purple-50 p-3.5">
                  {analysis && (
                    <>
                      <p className="text-[11px] font-semibold tracking-wide text-[#9333EA]">
                        SUMMARY
                      </p>
                      <p className="text-[13px] leading-relaxed text-foreground/70">
                        {analysis.summary}
                      </p>
                      {analysis.blockers && (
                        <>
                          <p className="text-[11px] font-semibold tracking-wide text-[#9333EA]">
                            DETECTED BLOCKERS
                          </p>
                          <p className="text-[13px] leading-relaxed text-foreground/70">
                            {analysis.blockers}
                          </p>
                        </>
                      )}
                    </>
                  )}
                  {aiNote && (
                    <p className="text-[13px] font-medium text-[#9333EA]">{aiNote}</p>
                  )}
                </div>
              )}
            </Section>
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        loading={deleting}
        danger
        title="Delete this task?"
        message="This task and its subtasks and links will be permanently removed. This can't be undone."
        confirmLabel="Delete task"
      />
    </>
  );
}

/* ---- small presentational helpers ---- */

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-foreground/50">{label}</label>
      {children}
    </div>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <div className="space-y-3 px-6 py-4">{children}</div>;
}

function SectionHeader({ title, trailing }: { title: string; trailing?: string }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="text-sm font-semibold">{title}</h3>
      {trailing && <span className="text-xs text-foreground/50">{trailing}</span>}
    </div>
  );
}

function Divider() {
  return <div className="h-px w-full bg-border" />;
}

function Select({
  value,
  onChange,
  children,
  className = "",
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`rounded-xl border border-border bg-input px-3 py-2.5 text-sm focus:border-foreground/40 focus:outline-none ${className}`}
    >
      {children}
    </select>
  );
}

function AiButton({
  onClick,
  busy,
  children,
}: {
  onClick: () => void;
  busy: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="flex items-center gap-1.5 rounded-full bg-purple-100 px-3.5 py-2 text-[13px] font-medium text-[#9333EA] transition-opacity hover:opacity-90 disabled:opacity-60"
    >
      {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  );
}
