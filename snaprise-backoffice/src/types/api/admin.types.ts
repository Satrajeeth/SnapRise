// Mirrors the admin_service lead schemas (admin_service/app/schemas/lead.py).
// Field names match the wire format (snake_case).

// ---- Enums ----
export type LeadStatus = "new" | "contacted" | "converted";
export type LeadSource = "board_invite" | "promotion";

// ---- Entities ----
export interface Lead {
  id: string;
  email: string;
  source: LeadSource;
  board_id?: string | null;
  invited_by?: string | null;
  status: LeadStatus;
  notes?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

// ---- Payloads ----
export interface LeadUpdate {
  status?: LeadStatus;
  notes?: string | null;
}

export interface LeadCreate {
  email: string;
  source?: LeadSource;
  notes?: string | null;
  metadata?: Record<string, unknown>;
}

// Filters accepted by the leads list / export endpoints.
export interface LeadFilters {
  status?: LeadStatus;
  source?: LeadSource;
  q?: string;
  limit?: number;
  offset?: number;
}

// The authenticated user as returned by auth_service /users/me. We only care
// about the superuser bit for gating, but carry the common fields too.
export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}
