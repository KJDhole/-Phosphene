import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

async function cachedGet<T>(_key: string, url: string, _staleMs: number = 30000): Promise<T> {
  const res = await api.get<T>(url);
  return res.data;
}

export interface Category {
  name: string;
  display_name: string;
  emoji: string;
  description: string;
  sources: { name: string; display_name: string; type: string }[];
}

export interface ArticleSummary {
  slug: string;
  category: string;
  title: string;
  date: string;
  formats: string[];
  review_status: ReviewStatus;
  quality_passed: boolean;
  evidence_count: number;
  issue_count: number;
  deployment_ready: boolean;
}

export type ReviewStatus = 'awaiting_review' | 'changes_requested' | 'approved' | 'not_required' | 'legacy_unverified';

export interface EvidenceItem {
  source_id: string;
  source_name: string;
  source_display_name?: string;
  title: string;
  url: string;
  published_at?: string;
  summary?: string;
  author?: string;
  metadata?: Record<string, unknown>;
}

export interface QualityReport {
  passed?: boolean;
  errors?: string[];
  warnings?: string[];
  cited_sources?: string[];
  evidence_count?: number;
}

export interface ArticleDetail {
  slug: string;
  category: string;
  title: string;
  date: string;
  formats: Record<string, string>;
  review_status: ReviewStatus;
  review_note: string;
  quality: QualityReport;
  evidence: EvidenceItem[];
  deployment_ready: boolean;
}

export interface RunStatus {
  running: boolean;
  current_category: string | null;
  task_id?: string | null;
  status?: string;
}

export async function fetchCategories(): Promise<Category[]> {
  return cachedGet<Category[]>('categories', '/categories', 60000);
}

export async function runCategory(category: string, use_scrapling: boolean = true): Promise<void> {
  await api.post(`/run/${category}`, null, {
    params: { debug: false, use_scrapling },
  });
}

export async function runBatch(categories: string[], use_scrapling: boolean = true): Promise<void> {
  await api.post('/run/batch', { categories, use_scrapling });
}

export async function stopRun(): Promise<void> {
  await api.post('/run/stop');
}

export async function getRunStatus(): Promise<RunStatus> {
  const res = await api.get<RunStatus>('/run/status');
  return res.data;
}

export async function fetchHistory(category?: string): Promise<ArticleSummary[]> {
  const key = category ? `history:${category}` : 'history:all';
  return cachedGet<ArticleSummary[]>(key, `/history${category ? `?category=${category}` : ''}`, 15000);
}

export async function fetchArticleDetail(slug: string, category?: string): Promise<ArticleDetail> {
  const params = category ? { category } : {};
  const res = await api.get<ArticleDetail>(`/history/${slug}`, { params });
  return res.data;
}

export async function deleteArticle(slug: string, category?: string): Promise<void> {
  const params = category ? { category } : {};
  await api.delete(`/history/${slug}`, { params });
}

export async function updateArticleReview(
  slug: string,
  category: string,
  status: 'awaiting_review' | 'changes_requested' | 'approved',
  note: string = '',
): Promise<ArticleDetail> {
  const res = await api.put<ArticleDetail>(`/history/${slug}/review`, { status, note }, {
    params: { category },
  });
  return res.data;
}

export async function fetchConfig(): Promise<string> {
  const res = await api.get<{ content: string }>('/config');
  return res.data.content;
}

export async function updateConfig(content: string): Promise<void> {
  await api.put('/config', { content });
}

export function createLogWebSocket(
  onLog: (data: any) => void,
  onStatus: (data: any) => void,
  onComplete: (data: any) => void,
): LogSocketHandle {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/api/ws/logs`;
  let ws: WebSocket | null = null;
  let retryCount = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let closedByClient = false;

  const clearTimers = () => {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    reconnectTimer = null;
    heartbeatTimer = null;
  };

  const connect = () => {
    if (closedByClient) return;
    ws = new WebSocket(url);
    ws.onopen = () => {
      retryCount = 0;
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      heartbeatTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;
        if (data.type === 'log') onLog(data);
        if (data.type === 'status') onStatus(data);
        if (data.type === 'complete') onComplete(data);
      } catch { /* ignore malformed server events */ }
    };

    ws.onclose = () => {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      heartbeatTimer = null;
      if (!closedByClient) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
        retryCount += 1;
        reconnectTimer = setTimeout(connect, delay);
      }
    };
  };
  connect();

  return {
    close: () => {
      closedByClient = true;
      clearTimers();
      ws?.close(1000, 'client cleanup');
    },
    get readyState() {
      return ws?.readyState ?? WebSocket.CLOSED;
    },
  };
}

export interface LogSocketHandle {
  close: () => void;
  readonly readyState: number;
}

export interface VideoStatusData {
  slug: string;
  status: 'pending' | 'generating' | 'done' | 'failed';
  progress: number;
  video_url: string | null;
  error: string | null;
  message: string | null;
}

export async function generateVideo(slug: string, category: string): Promise<VideoStatusData> {
  const res = await api.post<VideoStatusData>(`/video/generate/${slug}`, null, {
    params: { category },
  });
  return res.data;
}

export async function getVideoStatus(slug: string, category?: string): Promise<VideoStatusData> {
  const res = await api.get<VideoStatusData>(`/video/status/${slug}`, {
    params: category ? { category } : {},
  });
  return res.data;
}

export function getVideoUrl(slug: string, category?: string): string {
  const params = category ? `?category=${category}` : '';
  return `/api/video/${slug}${params}`;
}
