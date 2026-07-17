import { useEffect, useRef } from 'react';
import { Button } from 'antd';
import { ClearOutlined, DownloadOutlined } from '@ant-design/icons';

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
  compact?: boolean;
}

const labels: Record<string, string> = {
  info: 'INFO', success: 'DONE', error: 'ERROR', system: 'SYSTEM',
};

export default function LogViewer({ logs, onClear, compact = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScroll = useRef(true);

  useEffect(() => {
    if (autoScroll.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className={`process-log ${compact ? 'compact' : ''}`}>
      <div className="process-log-head">
        <span>PROCESS NOTES</span>
        <div>
          <b>{logs.length}</b>
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            href="/api/diagnostics/log"
            title="下载完整诊断日志"
            aria-label="下载完整诊断日志"
          />
          <Button type="text" size="small" icon={<ClearOutlined />} onClick={onClear} aria-label="清空日志" />
        </div>
      </div>
      <div
        className="process-log-body"
        ref={containerRef}
        onScroll={() => {
          const element = containerRef.current;
          if (!element) return;
          autoScroll.current = element.scrollHeight - element.scrollTop - element.clientHeight < 40;
        }}
      >
        {logs.length === 0 ? (
          <div className="log-empty">
            <i />
            <span>等待第一条生产记录</span>
          </div>
        ) : logs.map((entry, index) => (
          <div className={`process-log-row level-${entry.level}`} key={`${entry.timestamp}-${index}`}>
            <time>{entry.timestamp}</time>
            <b>{labels[entry.level] || entry.level.toUpperCase()}</b>
            <span>{entry.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
