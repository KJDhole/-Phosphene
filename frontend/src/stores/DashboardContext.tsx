import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { createLogWebSocket, getRunStatus } from '../api/client';
import type { LogEntry } from '../components/LogViewer';

interface DashboardState {
  selected: string[];
  setSelected: (selected: string[]) => void;
  isRunning: boolean;
  setIsRunning: (running: boolean) => void;
  logs: LogEntry[];
  clearLogs: () => void;
}

const DashboardContext = createContext<DashboardState | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  const connectWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const socket = createLogWebSocket(
      (data) => {
        setLogs((prev) => [...prev, {
          timestamp: data.timestamp,
          category: data.category,
          level: data.level,
          message: data.message,
          progress: data.progress,
        }]);
      },
      (data) => {
        setIsRunning(data.running);
      },
      (data) => {
        setIsRunning(false);
      },
    );
    wsRef.current = socket;
    return socket;
  }, []);

  // 组件挂载时：检查运行状态 + 连接 WebSocket
  useEffect(() => {
    getRunStatus().then((status) => setIsRunning(status.running));
    const socket = connectWs();
    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [connectWs]);

  // 运行中但 WebSocket 断开时重连
  useEffect(() => {
    if (isRunning && wsRef.current && wsRef.current.readyState !== WebSocket.OPEN) {
      connectWs();
    }
  }, [isRunning, connectWs]);

  return (
    <DashboardContext.Provider value={{
      selected,
      setSelected,
      isRunning,
      setIsRunning,
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
