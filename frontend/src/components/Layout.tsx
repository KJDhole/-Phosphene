import { Layout as AntLayout } from 'antd';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const { Content, Header } = AntLayout;

export default function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh', background: 'transparent' }}>
      <Sidebar />
      <AntLayout style={{
        background: 'transparent',
        marginLeft: 0,
      }}>
        <Header style={{
          background: 'rgba(255, 255, 255, 0.5)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          padding: '0 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(239, 231, 252, 0.8)',
          height: 64,
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}>
          <span style={{
            fontSize: 15,
            fontWeight: 600,
            color: '#1E1B4B',
            letterSpacing: '0.3px',
          }}>
            ✦ 熠觉 · Phosphene v2.1
          </span>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: '#10B981',
              display: 'inline-block',
            }} />
            <span style={{ fontSize: 13, color: '#64748B' }}>系统在线</span>
          </div>
        </Header>
        <Content style={{
          margin: 24,
          padding: 0,
          minHeight: 'calc(100vh - 64px - 48px)',
        }}>
          <div className="page-enter">
            <Outlet />
          </div>
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
