import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

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
}

export interface ArticleDetail {
  slug: string;
  category: string;
  title: string;
  date: string;
  formats: Record<string, string>;
}

export interface RunStatus {
  running: boolean;
  current_category: string | null;
}

export async function fetchCategories(): Promise<Category[]> {
  const res = await api.get<Category[]>('/categories');
  return res.data;
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
  const params = category ? { category } : {};
  const res = await api.get<ArticleSummary[]>('/history', { params });
  return res.data;
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
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/api/ws/logs`;
  const ws = new WebSocket(url);

  ws.onopen = () => {
    console.log('WebSocket 已连接:', url);
  };

  ws.onerror = () => {
    console.error('WebSocket 连接失败:', url);
  };

  ws.onclose = (e) => {
    console.log('WebSocket 已断开:', e.code, e.reason);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'log':
          onLog(data);
          break;
        case 'status':
          onStatus(data);
          break;
        case 'complete':
          onComplete(data);
          break;
      }
    } catch { /* ignore parse errors */ }
  };

  return ws;
}

export interface VideoStatusData {
  slug: string;
  status: 'pending' | 'generating' | 'done' | 'failed';
  progress: number;
  video_url: string | null;
  error: string | null;
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
