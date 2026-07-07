import { useState, useEffect, useCallback } from 'react';
import { Card, Space, Divider, Typography } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import CategoryPicker from '../components/CategoryPicker';
import RunControls from '../components/RunControls';
import LogViewer, { type LogEntry } from '../components/LogViewer';
import { createLogWebSocket, getRunStatus } from '../api/client';

const { Title } = Typography;

export default function Dashboard() {
  const [selected, setSelected] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const connectWs = useCallback(() => {
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
    setWs(socket);
    return socket;
  }, []);

  useEffect(() => {
    getRunStatus().then((status) => setIsRunning(status.running));
    const socket = connectWs();
    return () => {
      socket.close();
    };
  }, [connectWs]);

  useEffect(() => {
    if (isRunning && ws && ws.readyState !== WebSocket.OPEN) {
      const socket = connectWs();
      setWs(socket);
    }
  }, [isRunning, ws, connectWs]);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* Run Control Card */}
      <Card
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#7C3AED' }} />
            <span style={{ fontWeight: 600 }}>运行控制</span>
          </Space>
        }
        style={{ borderRadius: 12, overflow: 'hidden' }}
      >
        <CategoryPicker selected={selected} onChange={setSelected} />
        <Divider style={{ borderColor: 'rgba(124, 58, 237, 0.08)' }} />
        <RunControls
          selected={selected}
          isRunning={isRunning}
          onRunStart={() => {
            setLogs([]);
            setIsRunning(true);
          }}
        />
      </Card>

      {/* Log Viewer Card */}
      <Card
        style={{ borderRadius: 12, overflow: 'hidden' }}
      >
        <LogViewer
          logs={logs}
          onClear={() => setLogs([])}
        />
      </Card>
    </Space>
  );
}
