"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { adminApi } from "@/lib/api/admin";
import type { Lead, LeadStatus } from "@/types/api/admin.types";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/Button";
import { ArrowLeft, Loader2, Check } from "lucide-react";

const STATUS_OPTIONS: LeadStatus[] = ["new", "contacted", "converted"];

const selectClass =
  "h-11 w-full rounded-xl border border-border bg-input px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-border/60 py-3 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-foreground/50">{label}</span>
      <span className="text-sm font-medium break-all">{children}</span>
    </div>
  );
}

export default function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // Next 16: dynamic route params are a Promise — unwrap with `use()`.
  const { id } = use(params);
  const { token } = useAuth();

  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [status, setStatus] = useState<LeadStatus>("new");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const fetchLead = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.getLead(token, id);
      setLead(data);
      setStatus(data.status);
      setNotes(data.notes ?? "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load lead");
    } finally {
      setLoading(false);
    }
  }, [token, id]);

  useEffect(() => {
    fetchLead();
  }, [fetchLead]);

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    setSaved(false);
    try {
      const updated = await adminApi.updateLead(token, id, { status, notes });
      setLead(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Failed to update lead", err);
    } finally {
      setSaving(false);
    }
  };

  const dirty = !!lead && (status !== lead.status || notes !== (lead.notes ?? ""));

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href="/leads"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-foreground/60 transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to leads
      </Link>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-foreground/50" />
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-red-500">
          {error}
        </div>
      ) : lead ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-bold tracking-tight break-all">{lead.email}</h1>
            <StatusBadge status={lead.status} />
          </div>

          {/* ---- Editable: status + notes ---- */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="mb-4 text-sm font-semibold">Manage</h2>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="status">
                  Status
                </label>
                <select
                  id="status"
                  value={status}
                  onChange={(e) => setStatus(e.target.value as LeadStatus)}
                  className={selectClass}
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s[0].toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="notes">
                  Notes
                </label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  placeholder="Internal notes about this lead…"
                  className="w-full rounded-xl border border-border bg-input px-4 py-3 text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="flex items-center gap-3">
                <Button onClick={handleSave} disabled={!dirty || saving}>
                  {saving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : saved ? (
                    <Check className="mr-2 h-4 w-4" />
                  ) : null}
                  {saved ? "Saved" : "Save changes"}
                </Button>
              </div>
            </div>
          </div>

          {/* ---- Read-only details ---- */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="mb-2 text-sm font-semibold">Details</h2>
            <Field label="Source">
              {lead.source === "board_invite" ? "Board invite" : "Promotion"}
            </Field>
            <Field label="Board ID">
              {lead.board_id ? <span className="font-mono text-xs">{lead.board_id}</span> : "—"}
            </Field>
            <Field label="Invited by">
              {lead.invited_by ? <span className="font-mono text-xs">{lead.invited_by}</span> : "—"}
            </Field>
            <Field label="Created">{formatDateTime(lead.created_at)}</Field>
            <Field label="Updated">{formatDateTime(lead.updated_at)}</Field>
            {Object.keys(lead.metadata ?? {}).length > 0 && (
              <Field label="Metadata">
                <code className="font-mono text-xs">{JSON.stringify(lead.metadata)}</code>
              </Field>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
