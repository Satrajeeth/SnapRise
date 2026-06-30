"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { adminApi } from "@/lib/api/admin";
import type { Lead, LeadSource, LeadStatus } from "@/types/api/admin.types";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Loader2,
  Search,
  Download,
  ChevronLeft,
  ChevronRight,
  Users,
} from "lucide-react";

const PAGE_SIZE = 25;

const STATUS_OPTIONS: LeadStatus[] = ["new", "contacted", "converted"];
const SOURCE_OPTIONS: LeadSource[] = ["board_invite", "promotion"];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

const selectClass =
  "h-11 rounded-xl border border-border bg-input px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

export default function LeadsPage() {
  const { token } = useAuth();
  const router = useRouter();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Filters. `searchInput` is the live text box; `appliedQ` is what we actually
  // query with (applied on submit) so we don't fire a request per keystroke.
  const [status, setStatus] = useState<LeadStatus | "">("");
  const [source, setSource] = useState<LeadSource | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [offset, setOffset] = useState(0);

  const fetchLeads = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listLeads(token, {
        status: status || undefined,
        source: source || undefined,
        q: appliedQ || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setLeads(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [token, status, source, appliedQ, offset]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Any filter change resets pagination to the first page.
  const onStatusChange = (v: LeadStatus | "") => {
    setStatus(v);
    setOffset(0);
  };
  const onSourceChange = (v: LeadSource | "") => {
    setSource(v);
    setOffset(0);
  };
  const onSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(searchInput);
    setOffset(0);
  };

  const handleExport = async () => {
    if (!token) return;
    setExporting(true);
    try {
      const blob = await adminApi.exportLeads(token, {
        status: status || undefined,
        source: source || undefined,
        q: appliedQ || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "leads.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed", err);
    } finally {
      setExporting(false);
    }
  };

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Leads</h1>
        <p className="mt-1 text-sm text-foreground/50">
          {total} lead{total === 1 ? "" : "s"} captured from board invitations and promotions.
        </p>
      </div>

      {/* ---- Filter bar ---- */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <form onSubmit={onSearchSubmit} className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground/40" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search email or notes…"
            className="pl-9"
          />
        </form>

        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => onStatusChange(e.target.value as LeadStatus | "")}
          className={selectClass}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s[0].toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>

        <select
          aria-label="Filter by source"
          value={source}
          onChange={(e) => onSourceChange(e.target.value as LeadSource | "")}
          className={selectClass}
        >
          <option value="">All sources</option>
          {SOURCE_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "board_invite" ? "Board invite" : "Promotion"}
            </option>
          ))}
        </select>

        <Button variant="outline" onClick={handleExport} disabled={exporting || total === 0}>
          {exporting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          Export CSV
        </Button>
      </div>

      {/* ---- Table ---- */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-input/40 text-xs uppercase tracking-wide text-foreground/50">
              <tr>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Board</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-16 text-center">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin text-foreground/50" />
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={5} className="px-4 py-16 text-center text-sm text-red-500">
                    {error}
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-16 text-center">
                    <Users className="mx-auto mb-3 h-8 w-8 text-foreground/30" />
                    <p className="text-sm text-foreground/50">No leads match these filters.</p>
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr
                    key={lead.id}
                    onClick={() => router.push(`/leads/${lead.id}`)}
                    className="cursor-pointer border-b border-border/60 transition-colors last:border-0 hover:bg-input/40"
                  >
                    <td className="px-4 py-3 font-medium">{lead.email}</td>
                    <td className="px-4 py-3 text-foreground/70">
                      {lead.source === "board_invite" ? "Board invite" : "Promotion"}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground/50">
                      {lead.board_id ? lead.board_id.slice(0, 8) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="px-4 py-3 text-foreground/60">{formatDate(lead.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ---- Pagination ---- */}
      {!loading && !error && total > 0 && (
        <div className="mt-4 flex items-center justify-between text-sm text-foreground/60">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              Prev
            </Button>
            <Button
              variant="outline"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={page >= totalPages}
            >
              Next
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
