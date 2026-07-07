import { Button, Space, message, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  FastForwardOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { runCategory, runBatch, stopRun, fetchCategories } from '../api/client';

interface Props {
  selected: string[];
  isRunning: boolean;
  onRunStart: () => void;
}

export default function RunControls({ selected, isRunning, onRunStart }: Props) {
  const runSingleMutation = useMutation({
    mutationFn: () => {
      if (selected.length === 1) return runCategory(selected[0]);
      return runBatch(selected);
    },
    onSuccess: () => {
      onRunStart();
      message.success('任务已启动');
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.message || '启动失败');
    },
  });

  const runAllMutation = useMutation({
    mutationFn: async () => {
      const cats = await fetchCategories();
      return runBatch(cats.map((c) => c.name));
    },
    onSuccess: () => {
      onRunStart();
      message.success('全部任务已启动');
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.message || '启动失败');
    },
  });

  const stopMutation = useMutation({
    mutationFn: stopRun,
    onSuccess: () => message.success('已停止'),
    onError: (err: any) => {
      message.error(err?.response?.data?.message || '停止失败');
    },
  });

  return (
    <Space>
      <Tooltip title={selected.length === 0 ? '请先选择分类' : '运行选中的分类'}>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          disabled={selected.length === 0 || isRunning}
          loading={runSingleMutation.isPending}
          onClick={() => runSingleMutation.mutate()}
          style={{
            background: 'linear-gradient(135deg, #7C3AED 0%, #6366F1 100%)',
            border: 'none',
            boxShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
          }}
        >
          运行选中 ({selected.length})
        </Button>
      </Tooltip>
      <Button
        icon={<FastForwardOutlined />}
        disabled={isRunning}
        onClick={() => runAllMutation.mutate()}
        style={{
          borderColor: '#7C3AED',
          color: '#7C3AED',
          background: isRunning ? undefined : 'rgba(124, 58, 237, 0.06)',
        }}
      >
        运行全部
      </Button>
      <Button
        danger
        icon={<StopOutlined />}
        disabled={!isRunning}
        onClick={() => stopMutation.mutate()}
        className={isRunning ? 'btn-running' : ''}
        style={{
          background: isRunning ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : undefined,
          borderColor: isRunning ? '#EF4444' : '#D9D9D9',
          color: isRunning ? '#fff' : undefined,
        }}
      >
        停止
      </Button>
    </Space>
  );
}
