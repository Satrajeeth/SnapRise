// Generated from the SnapRise Board Service OpenAPI spec (/v1/openapi.json).
// Field names mirror the wire format (snake_case). Create/Update payloads are
// modeled separately from response entities, matching the API's own split.

// ---- Enums ----
export type LifecycleStage = "idea" | "active" | "paused" | "archived";
export type EncryptionStatus = "disabled" | "enabled" | "pending";
export type BoardRole = "owner" | "editor" | "viewer";
export type LinkType = "blocks" | "is_blocked_by" | "relates_to";

// ---- Boards ----
export interface Board {
  id: string;
  name: string;
  description?: string | null;
  lifecycle_stage: LifecycleStage;
  encryption_status: EncryptionStatus;
  settings: Record<string, unknown>;
  ai_metadata: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BoardDetailed extends Board {
  columns: ColumnWithTasks[];
}

export interface BoardCreate {
  name: string;
  description?: string | null;
  lifecycle_stage?: LifecycleStage;
  encryption_status?: EncryptionStatus;
  settings?: Record<string, unknown>;
  ai_metadata?: Record<string, unknown>;
  custom_fields?: Record<string, unknown>;
}

export interface BoardUpdate {
  name?: string | null;
  description?: string | null;
  lifecycle_stage?: LifecycleStage | null;
  encryption_status?: EncryptionStatus | null;
  settings?: Record<string, unknown> | null;
  ai_metadata?: Record<string, unknown> | null;
  custom_fields?: Record<string, unknown> | null;
}

// ---- Board members ----
export interface BoardMemberResponse {
  id: string;
  board_id: string;
  user_id: string;
  role: BoardRole;
  created_at: string;
  updated_at: string;
}

export interface BoardMemberCreate {
  user_id: string;
  role?: BoardRole;
}

export interface BoardMemberUpdate {
  role: BoardRole;
}

// ---- Columns ----
export interface Column {
  id: string;
  board_id: string;
  name: string;
  position: number;
  wip_limit?: number | null;
  settings: Record<string, unknown>;
  ai_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ColumnWithTasks extends Column {
  tasks: TaskWithSubtasks[];
}

export interface ColumnCreate {
  board_id: string;
  name: string;
  position?: number;
  wip_limit?: number | null;
  settings?: Record<string, unknown>;
  ai_metadata?: Record<string, unknown>;
}

export interface ColumnUpdate {
  name?: string | null;
  position?: number | null;
  wip_limit?: number | null;
  settings?: Record<string, unknown> | null;
  ai_metadata?: Record<string, unknown> | null;
}

// ---- Tasks ----
export interface Task {
  id: string;
  column_id: string;
  title: string;
  content?: string | null;
  position: number;
  encryption_status: EncryptionStatus;
  settings: Record<string, unknown>;
  ai_metadata: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TaskWithSubtasks extends Task {
  subtasks: Subtask[];
}

export interface TaskDetailed extends Task {
  subtasks: Subtask[];
  links: TaskLinkDetailed[];
}

export interface TaskMinimal {
  id: string;
  title: string;
  column_id: string;
}

export interface TaskCreate {
  column_id: string;
  title: string;
  content?: string | null;
  position?: number;
  encryption_status?: EncryptionStatus;
  settings?: Record<string, unknown>;
  ai_metadata?: Record<string, unknown>;
  custom_fields?: Record<string, unknown>;
}

export interface TaskUpdate {
  title?: string | null;
  content?: string | null;
  position?: number | null;
  column_id?: string | null;
  encryption_status?: EncryptionStatus | null;
  settings?: Record<string, unknown> | null;
  ai_metadata?: Record<string, unknown> | null;
  custom_fields?: Record<string, unknown> | null;
}

// ---- Task links ----
export interface TaskLink {
  id: string;
  source_task_id: string;
  target_task_id: string;
  link_type: LinkType;
  created_at: string;
}

export interface TaskLinkDetailed extends TaskLink {
  target_task?: TaskMinimal | null;
  source_task?: TaskMinimal | null;
}

export interface TaskLinkCreate {
  target_task_id: string;
  link_type: LinkType;
}

// ---- Subtasks ----
export interface Subtask {
  id: string;
  task_id: string;
  title: string;
  is_completed: boolean;
  position: number;
  settings: Record<string, unknown>;
  ai_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SubtaskCreate {
  task_id: string;
  title: string;
  is_completed?: boolean;
  position?: number;
  settings?: Record<string, unknown>;
  ai_metadata?: Record<string, unknown>;
}

export interface SubtaskUpdate {
  title?: string | null;
  is_completed?: boolean | null;
  position?: number | null;
  task_id?: string | null;
  settings?: Record<string, unknown> | null;
  ai_metadata?: Record<string, unknown> | null;
}

// ---- Templates ----
export interface ColumnTemplatePayload {
  name: string;
  position?: number;
  wip_limit?: number | null;
  settings?: Record<string, unknown>;
}

export interface BoardTemplatePayload {
  columns?: ColumnTemplatePayload[];
  settings?: Record<string, unknown>;
  custom_fields_schema?: Record<string, unknown>[];
}

export interface BoardTemplate {
  id: string;
  owner_user_id: string;
  name: string;
  description?: string | null;
  is_public: boolean;
  payload?: BoardTemplatePayload;
  created_at: string;
  updated_at: string;
}

export interface BoardTemplateCreate {
  name: string;
  description?: string | null;
  is_public?: boolean;
  payload?: BoardTemplatePayload;
}

export interface BoardTemplateUpdate {
  name?: string | null;
  description?: string | null;
  is_public?: boolean | null;
  payload?: BoardTemplatePayload | null;
}
