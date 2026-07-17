import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { createLogWebSocket, getRunStatus, type LogSocketHandle, type RunStatus } from '../api/client';
import { useQueryClient } from '@tanstack/react-query';
import type { LogEntry } from '../components/LogViewer';

interface DashboardState {
  selected: string[];
  setSelected: (selected: string[]) => void;
  isRunning: boolean;
  setIsRunning: (running: boolean) => void;
  runStatus: RunStatus;
  logs: LogEntry[];
  clearLogs: () => void;
}

// sessionStorage 持久化
const STORAGE_KEY_SELECTED = 'phosphene_selected';
const STORAGE_KEY_LOGS = 'phosphene_logs';

function loadSelected(): string[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_SELECTED);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveSelected(v: string[]) {
  try { sessionStorage.setItem(STORAGE_KEY_SELECTED, JSON.stringify(v)); } catch {}
}

function loadLogs(): LogEntry[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_LOGS);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveLogs(v: LogEntry[]) {
  try {
    // 只保留最近 200 条
    const trimmed = v.slice(-200);
    sessionStorage.setItem(STORAGE_KEY_LOGS, JSON.stringify(trimmed));
  } catch {}
}

const DashboardContext = createContext<DashboardState | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [selected, setSelectedState] = useState<string[]>(loadSelected);
  const [isRunning, setIsRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<RunStatus>({ running: false, current_category: null, status: 'idle' });
  const [logs, setLogs] = useState<LogEntry[]>(loadLogs);
  const wsRef = useRef<LogSocketHandle | null>(null);

  const setSelected = useCallback((v: string[]) => {
    setSelectedState(v);
    saveSelected(v);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
    saveLogs([]);
  }, []);

  const connectWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const socket = createLogWebSocket(
      (data) => {
        setLogs((prev) => {
          const next = [...prev, {
            timestamp: data.timestamp,
            category: data.category,
            level: data.level,
            message: data.message,
            progress: data.progress,
          }];
          saveLogs(next);
          return next;
        });
      },
      (data) => {
        setIsRunning(data.running);
        setRunStatus({
          running: data.running,
          current_category: data.current_category ?? null,
          task_id: data.task_id ?? null,
          status: data.status ?? (data.running ? 'running' : 'idle'),
        });
      },
      (_data) => {
        queryClient.invalidateQueries({ queryKey: ['history'] });
      },
    );
    wsRef.current = socket;
    return socket;
  }, [queryClient]);

  // 组件挂载时：检查运行状态 + 连接 WebSocket
  useEffect(() => {
    getRunStatus().then((status) => {
      setIsRunning(status.running);
      setRunStatus(status);
    }).catch(() => {
      setRunStatus({ running: false, current_category: null, status: 'offline' });
    });
    const socket = connectWs();
    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [connectWs]);

  return (
    <DashboardContext.Provider value={{
      selected,
      setSelected,
      isRunning,
      setIsRunning,
      runStatus,
      logs,
      clearLogs,
    }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard(): DashboardState {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('useDashboard must be used within DashboardProvider');
  return ctx;
}
