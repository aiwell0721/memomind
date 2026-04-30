const API_BASE = import.meta.env.VITE_API_BASE || '/api';

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('memomind_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return {} as T;
  return res.json();
}

export const api = {
  // Auth
  login: (username: string) => request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username }),
  }),
  me: () => request<Record<string, unknown>>('/auth/me'),

  // Notes
  notes: (params?: { limit?: number; offset?: number; workspace_id?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    if (params?.workspace_id) qs.set('workspace_id', String(params.workspace_id));
    return request<Note[]>(`/notes?${qs}`);
  },
  getNote: (id: number) => request<Note>(`/notes/${id}`),
  createNote: (data: { title: string; content: string; tags?: string[]; workspace_id?: number }) =>
    request<Note>('/notes', { method: 'POST', body: JSON.stringify(data) }),
  updateNote: (id: number, data: { title?: string; content?: string; tags?: string[] }) =>
    request<Note>(`/notes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteNote: (id: number) => request(`/notes/${id}`, { method: 'DELETE' }),
  searchNotes: (query: string, tags?: string[], limit = 20) =>
    request<SearchResult[]>('/notes/search', {
      method: 'POST',
      body: JSON.stringify({ query, tags, limit }),
    }),

  // Tags
  tags: (tree = false) => request<Tag[]>(`/tags?tree=${tree}`),
  createTag: (name: string, parent_id?: number) =>
    request<Tag>('/tags', { method: 'POST', body: JSON.stringify({ name, parent_id }) }),
  deleteTag: (id: number) => request(`/tags/${id}`, { method: 'DELETE' }),

  // Links
  outgoingLinks: (noteId: number) => request<Link[]>(`/links/outgoing/${noteId}`),
  incomingLinks: (noteId: number) => request<Link[]>(`/links/incoming/${noteId}`),
  linkGraph: () => request<Record<string, unknown>[]>('/links/graph'),
  brokenLinks: () => request<Record<string, unknown>[]>('/links/broken'),
  orphanedNotes: () => request<Record<string, unknown>[]>('/links/orphaned'),

  // Versions
  versions: (noteId: number, limit = 20) =>
    request<Version[]>(`/notes/${noteId}/versions?limit=${limit}`),
  saveVersion: (noteId: number, summary = '') =>
    request<Version>(`/notes/${noteId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ summary }),
    }),
  restoreVersion: (versionId: number) =>
    request(`/versions/${versionId}/restore`, { method: 'POST' }),

  // Workspaces
  workspaces: () => request<Workspace[]>('/workspaces'),
  getWorkspace: (id: number) => request<Workspace>(`/workspaces/${id}`),
  createWorkspace: (name: string, description = '') =>
    request<Workspace>('/workspaces', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),
  updateWorkspace: (id: number, name?: string, description?: string) =>
    request(`/workspaces/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description }),
    }),
  deleteWorkspace: (id: number) => request(`/workspaces/${id}`, { method: 'DELETE' }),
  moveNote: (noteId: number, targetWorkspaceId: number) =>
    request(`/notes/${noteId}/move?target_workspace_id=${targetWorkspaceId}`, { method: 'POST' }),

  // Users
  users: () => request<User[]>('/users'),
  createUser: (username: string, display_name = '') =>
    request<User>('/users', { method: 'POST', body: JSON.stringify({ username, display_name }) }),
  deleteUser: (id: number) => request(`/users/${id}`, { method: 'DELETE' }),

  // Activity
  activity: (params?: { workspace_id?: number; user_id?: number; note_id?: number; action?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.workspace_id) qs.set('workspace_id', String(params.workspace_id));
    if (params?.user_id) qs.set('user_id', String(params.user_id));
    if (params?.note_id) qs.set('note_id', String(params.note_id));
    if (params?.action) qs.set('action', params.action);
    if (params?.limit) qs.set('limit', String(params.limit));
    return request<ActivityLog[]>(`/activity?${qs}`);
  },
  noteActivity: (noteId: number, limit = 20) =>
    request<ActivityLog[]>(`/notes/${noteId}/activity?limit=${limit}`),

  // Backups
  backups: (limit = 50) => request<Backup[]>(`/backups?limit=${limit}`),
  createBackup: (description = '') =>
    request<Backup>('/backups', { method: 'POST', body: JSON.stringify({ description }) }),
  deleteBackup: (id: number) => request(`/backups/${id}`, { method: 'DELETE' }),

  // Health
  health: () => request<{ status: string; version: string }>('/health'),
};

// Types
export interface Note {
  id: number;
  title: string;
  content: string;
  tags: string[];
  workspace_id: number;
  created_at: string;
  updated_at: string;
}

export interface SearchResult {
  note: Note;
  score: number;
  highlights: string[];
}

export interface Tag {
  id: number;
  name: string;
  parent_id: number | null;
  children?: Tag[];
}

export interface Link {
  id: number;
  source_note_id: number;
  target_note_id: number;
  created_at: string;
}

export interface Version {
  id: number;
  note_id: number;
  title: string;
  content: string;
  tags: string[];
  change_summary: string;
  created_at: string;
}

export interface Workspace {
  id: number;
  name: string;
  description: string;
  created_at: string;
  note_count?: number;
}

export interface User {
  id: number;
  username: string;
  display_name: string;
  created_at: string;
}

export interface ActivityLog {
  id: number;
  action: string;
  user_id: number | null;
  workspace_id: number | null;
  note_id: number | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface Backup {
  id: number;
  path: string;
  description: string;
  size: number;
  created_at: string;
}
