// Domain types consumed by the board UI. These mirror the Board Service wire
// format but keep server-set / nested fields optional so the same shape works
// for both list responses (flat) and detailed responses (nested).
// The exhaustive, generated contract lives in ./api/board.types.

export type {
  LifecycleStage,
  EncryptionStatus,
  BoardRole,
  LinkType,
} from "./api/board.types";

export interface Subtask {
  id: string;
  task_id: string;
  title: string;
  is_completed: boolean;
  position: number;
  created_at?: string;
  updated_at?: string;
}

export interface Task {
  id: string;
  column_id: string;
  title: string;
  content?: string | null;
  position: number;
  subtasks?: Subtask[];
  created_at?: string;
  updated_at?: string;
}

export interface Column {
  id: string;
  board_id: string;
  name: string;
  position: number;
  wip_limit?: number | null;
  tasks?: Task[];
  created_at?: string;
  updated_at?: string;
}

export interface Board {
  id: string;
  name: string;
  description?: string | null;
  columns?: Column[];
  created_at?: string;
  updated_at?: string;
}
