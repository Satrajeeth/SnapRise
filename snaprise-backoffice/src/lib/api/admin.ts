import { apiRequest } from "../api";
import type {
  Lead,
  LeadCreate,
  LeadFilters,
  LeadListResponse,
  LeadUpdate,
} from "@/types/api/admin.types";

const ADMIN_BASE_URL = process.env.NEXT_PUBLIC_ADMIN_SERVICE_URL;

const withAuth = (token: string, options: RequestInit = {}): RequestInit => ({
  ...options,
  headers: {
    Authorization: `Bearer ${token}`,
    ...options.headers,
  },
});

// Build a `?status=&source=&q=&limit=&offset=` query string, omitting empties.
function buildQuery(filters: LeadFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.source) params.set("source", filters.source);
  if (filters.q && filters.q.trim()) params.set("q", filters.q.trim());
  if (filters.limit != null) params.set("limit", String(filters.limit));
  if (filters.offset != null) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const adminApi = {
  listLeads: (token: string, filters: LeadFilters = {}): Promise<LeadListResponse> =>
    apiRequest(ADMIN_BASE_URL, `/v1/leads${buildQuery(filters)}`, withAuth(token, { method: "GET" })),

  getLead: (token: string, leadId: string): Promise<Lead> =>
    apiRequest(ADMIN_BASE_URL, `/v1/leads/${leadId}`, withAuth(token, { method: "GET" })),

  updateLead: (token: string, leadId: string, updates: LeadUpdate): Promise<Lead> =>
    apiRequest(
      ADMIN_BASE_URL,
      `/v1/leads/${leadId}`,
      withAuth(token, { method: "PATCH", body: JSON.stringify(updates) })
    ),

  createLead: (token: string, lead: LeadCreate): Promise<Lead> =>
    apiRequest(
      ADMIN_BASE_URL,
      "/v1/leads",
      withAuth(token, { method: "POST", body: JSON.stringify(lead) })
    ),

  // CSV export returns a streamed text/csv body, not JSON — so it bypasses
  // apiRequest (which parses JSON) and returns a Blob the caller can download.
  exportLeads: async (token: string, filters: LeadFilters = {}): Promise<Blob> => {
    if (!ADMIN_BASE_URL) throw new Error("API Base URL is not defined");
    // Export ignores pagination — only the filter fields are meaningful.
    const query = buildQuery({
      status: filters.status,
      source: filters.source,
      q: filters.q,
    });
    const res = await fetch(`${ADMIN_BASE_URL}/v1/leads/export${query}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      throw new Error("Failed to export leads");
    }
    return res.blob();
  },
};
