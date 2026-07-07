import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

const { Sider } = Layout;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '控制面板',
  },
  {
    key: '/history',
    icon: <HistoryOutlined />,
    label: '历史记录',
  },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Sider
      width={220}
      theme="light"
      style={{
        background: 'rgba(255, 255, 255, 0.6)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderRight: '1px solid rgba(239, 231, 252, 0.8)',
        height: '100vh',
        position: 'sticky',
        top: 0,
        left: 0,
      }}
    >
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
      }}>
      {/* Brand */}
      <div style={{
        height: 72,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        borderBottom: '1px solid rgba(124, 58, 237, 0.1)',
        padding: '0 16px',
        userSelect: 'none',
      }}>
        <div style={{
          fontSize: 22,
          fontWeight: 800,
          background: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          letterSpacing: '0.5px',
        }}>
          ✦ 熠觉
        </div>
        <div style={{
          fontSize: 11,
          color: '#64748B',
          fontWeight: 500,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          marginTop: 2,
        }}>
          Phosphene
        </div>
      </div>

      {/* Menu - fill space */}
      <Menu
        mode="inline"
        selectedKeys={[location.pathname === '/' ? '/' : '/history']}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{
          background: 'transparent',
          borderRight: 'none',
          padding: '8px 0',
          flex: 1,
        }}
      />

      {/* Bottom */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid rgba(124, 58, 237, 0.08)',
        fontSize: 11,
        color: '#94A3B8',
        textAlign: 'center',
        letterSpacing: '0.5px',
      }}>
        ✦ 熠觉 · Phosphene
      </div>
      </div>
    </Sider>
  );
}
