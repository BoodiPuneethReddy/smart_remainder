/**
 * lib/api.ts — Axios instance with JWT interceptor + typed API functions.
 * The frontend only knows about the backend. It has no knowledge of the AI service.
 */
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// ── JWT request interceptor ─────────────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Auth redirect on 401 ────────────────────────────────────────────────────
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);

export function getErrorMessage(err: any): string {
  if (!err.response) {
    return 'Connection error. Please try again.';
  }
  if (err.response.status >= 500) {
    return 'Something went wrong. Please try again.';
  }
  const detail = err.response.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0].msg || 'Invalid input provided.';
  }
  return 'An error occurred. Please try again.';
}


// ── Types ────────────────────────────────────────────────────────────────────
export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  college_id?: number;
  college?: string;
  custom_college?: string;
  department?: string;
  year?: string;
  preferences?: string;
  created_at: string;
}

export interface Task {
  id: number;
  user_id: number;
  title: string;
  subject: string;
  description: string;
  task_type: string;
  due_date: string;
  estimated_hours: number;
  is_completed: boolean;
  completed_at: string | null;
  priority_score: number;
  urgency_score: number;
  importance_score: number;
  weakness_score: number;
  effort_score: number;
  ai_explanation: string;
  created_at: string;
  exam_room?: string;
  exam_duration_minutes?: number;
  grade_weight?: number;
  imported_from_id?: number | null;
}

export interface DailyPlanTask {
  task_id: number;
  title: string;
  subject: string;
  task_type: string;
  due_date: string;
  priority_score: number;
  urgency_score: number;
  importance_score: number;
  weakness_score: number;
  effort_score: number;
  ai_explanation: string;
  recommended_minutes: number;
}

export interface DailyPlan {
  date: string;
  total_recommended_minutes: number;
  tasks: DailyPlanTask[];
}

export interface Notification {
  id: number;
  user_id: number;
  task_id: number | null;
  urgency_tier: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface StepLog {
  agent_name: string;
  status: 'completed' | 'warning' | 'pending' | 'running';
  summary: string;
  timestamp?: string;
}

export interface ChatMessage {
  question: string;
  answer: string;
  created_at: string;
  primary_intent?: string;
  step_logs?: StepLog[];
}

export interface AnalyticsSummary {
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  total_study_minutes: number;
  avg_priority_score: number;
  subjects: SubjectStat[];
  pending_by_type: Record<string, number>;
  streak_days: number;
}

export interface SubjectStat {
  subject: string;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  total_study_minutes: number;
  avg_priority_score: number;
}

export interface WeeklyDataPoint {
  date: string;
  completed: number;
  added: number;
  study_minutes: number;
}

// ── Auth API ────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<{ access_token: string; user: User }>('/api/auth/login', { email, password }),
  register: (data: { email: string; full_name: string; password: string; college_id?: number; custom_college?: string; department?: string; year?: string; date_of_birth?: string }) =>
    apiClient.post<{ access_token: string; user: User }>('/api/auth/register', data),
  me: () => apiClient.get<User>('/api/auth/me'),
  updateProfile: (data: Partial<User>) => apiClient.put<User>('/api/auth/me', data),
  logout: () => apiClient.post<{ message: string }>('/api/auth/logout'),
  refresh: () => apiClient.post<{ access_token: string; user: User }>('/api/auth/refresh'),
  forgotPassword: (email: string) =>
    apiClient.post<{ message: string; dev_otp?: string; expires_in_minutes: number }>('/api/auth/forgot-password', { email }),
  verifyOtp: (email: string, otp: string) =>
    apiClient.post<{ reset_token: string }>('/api/auth/verify-otp', { email, otp }),
  resetPassword: (reset_token: string, new_password: string) =>
    apiClient.post<{ message: string }>('/api/auth/reset-password', { reset_token, new_password }),
};

// ── Colleges API ─────────────────────────────────────────────────────
export interface College {
  id: number;
  college_name: string;
  university?: string;
  state: string;
  district?: string;
}

export const collegesApi = {
  search: (q: string) =>
    apiClient.get<College[]>(`/api/colleges/search?q=${encodeURIComponent(q)}&limit=20`),
};

// ── Import API ───────────────────────────────────────────────────────────
export interface ImportFieldPreview {
  field_name: string;
  display_label: string;
  value: string | null;
  confidence: 'high' | 'medium' | 'low' | 'not_found';
}

export interface ImportSection {
  document_type: string;
  display_name: string;
  fields: ImportFieldPreview[];
  missing_required: string[];
  possible_duplicates: { id: number; title: string; due_date: string }[];
}

export interface ImportPreview {
  import_id: number;
  original_filename: string;
  document_type: string;
  classification_confidence: number;
  sections: ImportSection[];
  is_mixed: boolean;
  is_unknown: boolean;
  ocr_used: boolean;
  extracted_text_snippet: string;
}

export interface ImportHistoryItem {
  id: number;
  original_filename: string;
  document_type: string;
  status: 'pending_review' | 'approved' | 'rejected';
  confidence_overall: number;
  uploaded_at: string;
  reviewed_at: string | null;
}

export const importApi = {
  capabilities: () =>
    apiClient.get<{ pdf: boolean; image: boolean; ocr_message: string | null }>('/api/import/capabilities'),
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post<ImportPreview>('/api/import/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
  },
  approve: (import_id: number, reviewed_sections: { document_type: string; fields: Record<string, string> }[]) =>
    apiClient.post('/api/import/approve', { import_id, reviewed_sections }),
  history: () =>
    apiClient.get<ImportHistoryItem[]>('/api/import/history'),
  viewSource: (import_id: number) =>
    `${BASE_URL}/api/import/${import_id}/source`,
};

// ── Tasks API ──────────────────────────────────────────────────────────────
export const tasksApi = {
  list: (params?: { include_completed?: boolean; subject?: string; task_type?: string }) =>
    apiClient.get<{ tasks: Task[]; total: number }>('/api/tasks', { params }),
  create: (data: Partial<Task>) => apiClient.post<Task>('/api/tasks', data),
  update: (id: number, data: Partial<Task>) => apiClient.patch<Task>(`/api/tasks/${id}`, data),
  delete: (id: number) => apiClient.delete(`/api/tasks/${id}`),
};

// ── Planner API ──────────────────────────────────────────────────────────────
export const plannerApi = {
  daily: () => apiClient.get<DailyPlan>('/api/planner/daily'),
  weekly: () => apiClient.get<any>('/api/planner/weekly'),
  rescore: () => apiClient.post<{ tasks: Task[]; total: number }>('/api/planner/score'),
};

// ── Chat API ────────────────────────────────────────────────────────────────
export const chatApi = {
  ask: (question: string, documentId?: number) =>
    apiClient.post<ChatMessage>('/api/chat', {
      question,
      ...(documentId !== undefined ? { document_id: documentId } : {}),
    }, { timeout: 30000 }),
  history: () => apiClient.get<ChatMessage[]>('/api/chat/history'),
};

// ── Reminders API ─────────────────────────────────────────────────────────────
export const remindersApi = {
  list: () => apiClient.get<Notification[]>('/api/reminders'),
  check: () => apiClient.post<Notification[]>('/api/reminders/check'),
  markRead: (id: number) => apiClient.put(`/api/reminders/${id}/read`),
  markAllRead: () => apiClient.put('/api/reminders/read-all'),
};

// ── Analytics API ─────────────────────────────────────────────────────────────
export const analyticsApi = {
  summary: () => apiClient.get<AnalyticsSummary>('/api/analytics/summary'),
  weekly: () => apiClient.get<{ weekly_data: WeeklyDataPoint[]; total_this_week: number; completed_this_week: number }>('/api/analytics/weekly'),
  getLatestTelemetry: () => apiClient.get<any>('/api/analytics/telemetry/latest'),
  getKnowledgeGraph: () => apiClient.get<any>('/api/analytics/knowledge-graph'),
};

export const api = {
  getLatestTelemetry: analyticsApi.getLatestTelemetry,
  getKnowledgeGraph: analyticsApi.getKnowledgeGraph,
};

// ── Assessment API ────────────────────────────────────────────────────────────
export interface TopicAnalytics {
  id: number;
  subject: string;
  topic: string;
  mastery: number;
  confidence: number;
  retention: number;
  avg_quiz_score: number;
  attempts_count: number;
  revision_count: number;
  interval_days: number;
  learning_streak: number;
  last_revision: string;
}

export interface QuizQuestion {
  id: string;
  question_text: string;
  options: string[];
}

export interface QuizResponse {
  topic: string;
  subject: string;
  questions: QuizQuestion[];
}

export interface QuestionEvaluation {
  question_id: string;
  is_correct: boolean;
  explanation: string;
}

export interface SubmitResponse {
  status: 'SUCCESS' | 'SPEED_GUESS_DETECTED';
  message: string;
  score?: number;
  correct_count?: number;
  total_questions?: number;
  evaluations?: QuestionEvaluation[];
}

export interface CitationResponse {
  question_text: string;
  correct_answer: string;
  document_name: string | null;
  page_range: string | null;
  retrieved_context: string | null;
  generated_rubric: string | null;
}

export const assessmentApi = {
  generate: (subject: string, topic: string, documentId?: number) =>
    apiClient.post<QuizResponse>('/api/assessment/generate', { subject, topic, document_id: documentId }),
  submit: (answers: Record<string, string>, timeTakenSeconds: number) =>
    apiClient.post<SubmitResponse>('/api/assessment/submit', { answers, time_taken_seconds: timeTakenSeconds }),
  citation: (questionId: number) =>
    apiClient.get<CitationResponse>(`/api/assessment/citation/${questionId}`),
  getLearningProfile: () =>
    apiClient.get<TopicAnalytics[]>('/api/assessment/learning-profile'),
  listMistakes: () =>
    apiClient.get<any[]>('/api/assessment/tutor/mistake-journal'),
};
