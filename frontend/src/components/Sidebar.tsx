import { useLocation, useNavigate } from 'react-router-dom';
import {
  FileTextOutlined,
  HomeOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useDashboard } from '../stores/DashboardContext';

const items = [
  { path: '/', label: '今日生产', caption: 'PRODUCE', icon: <HomeOutlined /> },
  { path: '/review', label: '内容审核', caption: 'REVIEW', icon: <SafetyCertificateOutlined /> },
  { path: '/history', label: '内容档案', caption: 'ARCHIVE', icon: <FileTextOutlined /> },
];

export default function Sidebar({ compact = false }: { compact?: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isRunning, runStatus } = useDashboard();

  const isSelected = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  return (
    <aside className={`editorial-sidebar ${compact ? 'compact' : ''}`}>
      <button className="brand-lockup" onClick={() => navigate('/')} aria-label="返回首页">
        <span className="phosphene-mark" aria-hidden="true">
          <i />
        </span>
        <span className="brand-copy">
          <strong>熠觉</strong>
          <small>PHOSPHENE</small>
        </span>
      </button>

      <nav className="editorial-nav" aria-label="主导航">
        {items.map((item, index) => (
          <button
            key={item.path}
            className={isSelected(item.path) ? 'active' : ''}
            onClick={() => navigate(item.path)}
            title={compact ? item.label : undefined}
          >
            <span className="nav-index">0{index + 1}</span>
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-copy">
              <strong>{item.label}</strong>
              <small>{item.caption}</small>
            </span>
          </button>
        ))}
      </nav>

      <div className="system-strip">
        <div className="system-strip-head">
          <span className={`system-dot ${isRunning ? 'running' : ''}`} />
          <strong>{isRunning ? '内容流转中' : '系统就绪'}</strong>
        </div>
        <div className="system-row">
          <span>AI PIPELINE</span>
          <b>{runStatus.status === 'offline' ? 'OFFLINE' : 'ONLINE'}</b>
        </div>
        <div className="system-row">
          <span>VERSION</span>
          <b>2.2 / R1</b>
        </div>
      </div>
    </aside>
  );
}
