export interface Board {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBoardRequest {
  name: string;
  description?: string;
}

export interface UpdateBoardRequest {
  name?: string;
  description?: string;
}

export interface BoardMember {
  user_id: string;
  role: 'admin' | 'editor' | 'viewer';
}

export interface AddBoardMemberRequest {
  user_id: string;
  role: 'admin' | 'editor' | 'viewer';
}

export interface Column {
  id: string;
  board_id: string;
  name: string;
  order: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateColumnRequest {
  board_id: string;
  name: string;
  order: number;
}

export interface UpdateColumnRequest {
  name?: string;
  order?: number;
}

export interface Task {
  id: string;
  column_id: string;
  title: string;
  content?: string;
  order: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateTaskRequest {
  column_id: string;
  title: string;
  content?: string;
  order: number;
}

export interface UpdateTaskRequest {
  title?: string;
  content?: string;
  order?: number;
}

export interface CreateTaskLinkRequest {
  target_task_id: string;
  link_type: 'blocks' | 'is_blocked_by' | 'relates_to' | 'duplicates';
}

export interface Subtask {
  id: string;
  task_id: string;
  title: string;
  is_completed: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateSubtaskRequest {
  task_id: string;
  title: string;
}

export interface UpdateSubtaskRequest {
  title?: string;
  is_completed?: boolean;
}

export interface Template {
  id: string;
  name: string;
  description?: string;
  is_public: boolean;
  columns?: any[];
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  is_public?: boolean;
  columns?: any[];
}
