import { Card, Space, Divider, Typography } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import CategoryPicker from '../components/CategoryPicker';
import RunControls from '../components/RunControls';
import LogViewer from '../components/LogViewer';
import { useDashboard } from '../stores/DashboardContext';

const { Title } = Typography;

export default function Dashboard() {
  const { selected, setSelected, isRunning, setIsRunning, logs, clearLogs } = useDashboard();

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
            clearLogs();
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
          onClear={clearLogs}
        />
      </Card>
    </Space>
  );
}
