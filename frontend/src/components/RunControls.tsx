import { Button, Switch, message } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { fetchCategories, runBatch, runCategory, stopRun } from '../api/client';

interface Props {
  selected: string[];
  isRunning: boolean;
  onBeforeRun?: () => void;
  onRunStart: () => void;
}

function apiError(error: any, fallback: string) {
  return error?.response?.data?.detail || error?.response?.data?.message || fallback;
}

export default function RunControls({ selected, isRunning, onBeforeRun, onRunStart }: Props) {
  const [useScrapling, setUseScrapling] = useState(true);

  const selectedMutation = useMutation({
    mutationFn: () => (
      selected.length === 1
        ? runCategory(selected[0], useScrapling)
        : runBatch(selected, useScrapling)
    ),
    onSuccess: () => {
      onRunStart();
      message.success('生产任务已进入队列');
    },
    onError: (error) => message.error(apiError(error, '启动失败')),
  });

  const allMutation = useMutation({
    mutationFn: async () => {
      const categories = await fetchCategories();
      return runBatch(categories.map((category) => category.name), useScrapling);
    },
    onSuccess: () => {
      onRunStart();
      message.success('全部分类已进入生产队列');
    },
    onError: (error) => message.error(apiError(error, '启动失败')),
  });

  const stopMutation = useMutation({
    mutationFn: stopRun,
    onSuccess: () => message.success('已发出停止请求'),
    onError: (error) => message.error(apiError(error, '停止失败')),
  });

  const pending = selectedMutation.isPending || allMutation.isPending;

  return (
    <div className="run-controls">
      <div className="collection-mode">
        <div>
          <span className="control-label">采集策略</span>
          <strong>{useScrapling ? '浏览器增强采集' : 'HTTP 直连采集'}</strong>
          <small>{useScrapling ? '对反爬页面进行渲染，耗时更长' : '速度更快，可能遗漏动态页面'}</small>
        </div>
        <Switch checked={useScrapling} onChange={setUseScrapling} disabled={isRunning} />
      </div>

      <div className="run-action-row">
        {isRunning ? (
          <Button
            danger
            size="large"
            icon={<StopOutlined />}
            loading={stopMutation.isPending}
            onClick={() => stopMutation.mutate()}
          >
            停止当前生产
          </Button>
        ) : (
          <Button
            type="primary"
            size="large"
            icon={<PlayCircleOutlined />}
            disabled={selected.length === 0}
            loading={pending}
            onClick={() => {
              onBeforeRun?.();
              selectedMutation.mutate();
            }}
          >
            开始生产 {selected.length > 0 ? `· ${selected.length} 个分类` : ''}
          </Button>
        )}
        <Button
          type="text"
          disabled={isRunning || pending}
          onClick={() => {
            onBeforeRun?.();
            allMutation.mutate();
          }}
        >
          运行全部分类
        </Button>
      </div>
    </div>
  );
}
