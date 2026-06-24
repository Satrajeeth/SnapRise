import { apiRequest } from "../api";
import type {
  Board,
  BoardDetailed,
  BoardCreate,
  BoardUpdate,
  BoardMemberResponse,
  BoardMemberCreate,
  BoardMemberUpdate,
  BoardRole,
  Column,
  ColumnCreate,
  ColumnUpdate,
  Task,
  TaskDetailed,
  TaskCreate,
  TaskUpdate,
  TaskLink,
  TaskLinkCreate,
  Subtask,
  SubtaskCreate,
  SubtaskUpdate,
  BoardTemplate,
  BoardTemplateCreate,
  BoardTemplateUpdate,
} from "@/types/api/board.types";

const BOARD_BASE_URL = process.env.NEXT_PUBLIC_BOARD_SERVICE_URL;

const withAuth = (token: string, options: RequestInit = {}): RequestInit => ({
  ...options,
  headers: {
    Authorization: `Bearer ${token}`,
    ...options.headers,
  },
});

const jsonBody = (token: string, method: string, body?: unknown): RequestInit =>
  withAuth(token, {
    method,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

export const boardApi = {
  // ---- Boards ----
  getBoards: (token: string): Promise<Board[]> =>
    apiRequest(BOARD_BASE_URL, "/v1/boards", withAuth(token, { method: "GET" })),

  getBoard: (token: string, boardId: string): Promise<BoardDetailed> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}`, withAuth(token, { method: "GET" })),

  createBoard: (token: string, name: string, description?: string): Promise<Board> =>
    apiRequest(BOARD_BASE_URL, "/v1/boards", jsonBody(token, "POST", {
      name,
      description,
    } satisfies BoardCreate)),

  updateBoard: (token: string, boardId: string, updates: BoardUpdate): Promise<Board> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}`, jsonBody(token, "PATCH", updates)),

  deleteBoard: (token: string, boardId: string): Promise<void> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}`, withAuth(token, { method: "DELETE" })),

  createBoardFromTemplate: (token: string, templateId: string, boardName: string): Promise<Board> =>
    apiRequest(
      BOARD_BASE_URL,
      `/v1/boards/from-template?template_id=${encodeURIComponent(templateId)}&board_name=${encodeURIComponent(boardName)}`,
      withAuth(token, { method: "POST" })
    ),

  // ---- Board members ----
  getBoardMembers: (token: string, boardId: string): Promise<BoardMemberResponse[]> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}/members`, withAuth(token, { method: "GET" })),

  addBoardMember: (
    token: string,
    boardId: string,
    userId: string,
    role: BoardRole = "viewer"
  ): Promise<BoardMemberResponse> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}/members`, jsonBody(token, "POST", {
      user_id: userId,
      role,
    } satisfies BoardMemberCreate)),

  updateBoardMember: (
    token: string,
    boardId: string,
    targetUserId: string,
    role: BoardRole
  ): Promise<BoardMemberResponse> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}/members/${targetUserId}`, jsonBody(token, "PUT", {
      role,
    } satisfies BoardMemberUpdate)),

  removeBoardMember: (token: string, boardId: string, targetUserId: string): Promise<void> =>
    apiRequest(
      BOARD_BASE_URL,
      `/v1/boards/${boardId}/members/${targetUserId}`,
      withAuth(token, { method: "DELETE" })
    ),

  // ---- Columns ----
  createColumn: (token: string, boardId: string, name: string, position: number): Promise<Column> =>
    apiRequest(BOARD_BASE_URL, "/v1/columns", jsonBody(token, "POST", {
      board_id: boardId,
      name,
      position,
    } satisfies ColumnCreate)),

  updateColumn: (token: string, columnId: string, updates: ColumnUpdate): Promise<Column> =>
    apiRequest(BOARD_BASE_URL, `/v1/columns/${columnId}`, jsonBody(token, "PATCH", updates)),

  deleteColumn: (token: string, columnId: string): Promise<void> =>
    apiRequest(BOARD_BASE_URL, `/v1/columns/${columnId}`, withAuth(token, { method: "DELETE" })),

  // ---- Tasks ----
  getTask: (token: string, taskId: string, includeLinkedTasks = false): Promise<TaskDetailed> =>
    apiRequest(
      BOARD_BASE_URL,
      `/v1/tasks/${taskId}?include_linked_tasks=${includeLinkedTasks}`,
      withAuth(token, { method: "GET" })
    ),

  createTask: (
    token: string,
    columnId: string,
    title: string,
    content: string = "",
    position: number
  ): Promise<Task> =>
    apiRequest(BOARD_BASE_URL, "/v1/tasks", jsonBody(token, "POST", {
      column_id: columnId,
      title,
      content,
      position,
    } satisfies TaskCreate)),

  updateTask: (token: string, taskId: string, updates: TaskUpdate): Promise<Task> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/${taskId}`, jsonBody(token, "PATCH", updates)),

  deleteTask: (token: string, taskId: string): Promise<void> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/${taskId}`, withAuth(token, { method: "DELETE" })),

  // ---- Task links ----
  createTaskLink: (token: string, taskId: string, link: TaskLinkCreate): Promise<TaskLink> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/${taskId}/links`, jsonBody(token, "POST", link)),

  deleteTaskLink: (token: string, linkId: string): Promise<void> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/links/${linkId}`, withAuth(token, { method: "DELETE" })),

  // ---- Subtasks ----
  createSubtask: (token: string, taskId: string, title: string): Promise<Subtask> =>
    apiRequest(BOARD_BASE_URL, "/v1/subtasks", jsonBody(token, "POST", {
      task_id: taskId,
      title,
    } satisfies SubtaskCreate)),

  updateSubtask: (token: string, subtaskId: string, updates: SubtaskUpdate): Promise<Subtask> =>
    apiRequest(BOARD_BASE_URL, `/v1/subtasks/${subtaskId}`, jsonBody(token, "PATCH", updates)),

  deleteSubtask: (token: string, subtaskId: string): Promise<void> =>
    apiRequest(BOARD_BASE_URL, `/v1/subtasks/${subtaskId}`, withAuth(token, { method: "DELETE" })),

  // ---- Templates ----
  getTemplates: (token: string): Promise<BoardTemplate[]> =>
    apiRequest(BOARD_BASE_URL, "/v1/templates", withAuth(token, { method: "GET" })),

  getTemplate: (token: string, templateId: string): Promise<BoardTemplate> =>
    apiRequest(BOARD_BASE_URL, `/v1/templates/${templateId}`, withAuth(token, { method: "GET" })),

  createTemplate: (token: string, template: BoardTemplateCreate): Promise<BoardTemplate> =>
    apiRequest(BOARD_BASE_URL, "/v1/templates", jsonBody(token, "POST", template)),

  updateTemplate: (token: string, templateId: string, updates: BoardTemplateUpdate): Promise<BoardTemplate> =>
    apiRequest(BOARD_BASE_URL, `/v1/templates/${templateId}`, jsonBody(token, "PATCH", updates)),

  deleteTemplate: (token: string, templateId: string): Promise<void> =>
    apiRequest(BOARD_BASE_URL, `/v1/templates/${templateId}`, withAuth(token, { method: "DELETE" })),

  // ---- AI & smart features ----
  analyzeTask: (token: string, taskId: string): Promise<Record<string, unknown>> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/${taskId}/ai-analyze`, withAuth(token, { method: "POST" })),

  classifyTask: (token: string, taskId: string): Promise<Record<string, unknown>> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/${taskId}/ai-classify`, withAuth(token, { method: "POST" })),

  suggestTaskColumn: (token: string, taskId: string): Promise<Record<string, unknown>> =>
    apiRequest(BOARD_BASE_URL, `/v1/tasks/${taskId}/suggest-column`, withAuth(token, { method: "POST" })),

  smartSortBoard: (token: string, boardId: string): Promise<Record<string, unknown>> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}/smart-sort`, withAuth(token, { method: "POST" })),

  getBoardMetrics: (token: string, boardId: string): Promise<Record<string, unknown>> =>
    apiRequest(BOARD_BASE_URL, `/v1/boards/${boardId}/metrics`, withAuth(token, { method: "GET" })),
};
