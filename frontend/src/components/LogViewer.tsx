import { useEffect, useRef } from 'react';
import { Button, Space, Tag } from 'antd';
import { ClearOutlined, VerticalAlignBottomOutlined, ConsoleSqlOutlined } from '@ant-design/icons';

export interface LogEntry {
  timestamp: string;
  category: string;
  level: string;
  message: string;
  progress: number;
}

interface Props {
  logs: LogEntry[];
  onClear: () => void;
}

const levelLabels: Record<string, string> = {
  info: 'INFO',
  success: 'OK',
  error: 'ERR',
  system: 'SYS',
};

export default function LogViewer({ logs, onClear }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    autoScrollRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
  };

  const levelColors: Record<string, string> = {
    info: 'default',
    success: 'success',
    error: 'error',
    system: 'processing',
  };

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Space>
          <ConsoleSqlOutlined style={{ color: '#7C3AED' }} />
          <span style={{ fontWeight: 600 }}>运行日志</span>
        </Space>
        <Button size="small" icon={<ClearOutlined />} onClick={onClear}>
          清空
        </Button>
        <Button
          size="small"
          icon={<VerticalAlignBottomOutlined />}
          onClick={() => {
            autoScrollRef.current = true;
            if (containerRef.current) {
              containerRef.current.scrollTop = containerRef.current.scrollHeight;
            }
          }}
        >
          自动滚动
        </Button>
        <Tag
          style={{
            background: 'rgba(124, 58, 237, 0.08)',
            border: '1px solid rgba(124, 58, 237, 0.2)',
            color: '#7C3AED',
            borderRadius: 4,
          }}
        >
          {logs.length} 条
        </Tag>
      </Space>
      <div
        ref={containerRef}
        className="log-viewer"
        onScroll={handleScroll}
      >
        {logs.length === 0 && (
          <div style={{
            color: '#6B5B8A',
            textAlign: 'center',
            paddingTop: 80,
            fontSize: 14,
            opacity: 0.6,
          }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>⚡</div>
            选择分类并点击「运行」开始
          </div>
        )}
        {logs.map((entry, i) => (
          <div key={i} className={`log-entry log-${entry.level}`}>
            <span className="timestamp">[{entry.timestamp}]</span>
            <span style={{
              display: 'inline-block',
              width: 32,
              fontSize: 11,
              fontWeight: 600,
              opacity: 0.7,
              marginRight: 6,
            }}>
              {levelLabels[entry.level] || entry.level.toUpperCase()}
            </span>
            {entry.message}
          </div>
        ))}
      </div>
    </div>
  );
}
