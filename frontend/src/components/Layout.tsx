import { useState } from 'react';
import { Button, Tooltip } from 'antd';
import { EyeOutlined, FullscreenExitOutlined } from '@ant-design/icons';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

const pageNames: Record<string, string> = {
  '/': '今日生产',
  '/review': '内容审核',
  '/history': '内容档案',
};

function currentPage(pathname: string) {
  if (pathname.startsWith('/video/')) return '视频工作室';
  if (pathname.startsWith('/history/')) return '内容审核室';
  return pageNames[pathname] || '熠觉';
}

export default function Layout() {
  const location = useLocation();
  const [focusMode, setFocusMode] = useState(false);
  const date = new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date());

  return (
    <div className={`app-shell ${focusMode ? 'focus-mode' : ''}`}>
      <Sidebar compact={focusMode} />
      <div className="app-stage">
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-kicker">PHOSPHENE / EDITORIAL OS</span>
            <span className="topbar-divider" />
            <strong>{currentPage(location.pathname)}</strong>
          </div>
          <div className="topbar-actions">
            <span className="topbar-date">{date}</span>
            <Tooltip title={focusMode ? '退出聚焦视图' : '进入演示聚焦视图'}>
              <Button
                type="text"
                className="focus-toggle"
                icon={focusMode ? <FullscreenExitOutlined /> : <EyeOutlined />}
                onClick={() => setFocusMode((value) => !value)}
              >
                {focusMode ? '退出聚焦' : '聚焦视图'}
              </Button>
            </Tooltip>
          </div>
        </header>
        <main className="app-content">
          <div className="page-enter" key={location.pathname}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
