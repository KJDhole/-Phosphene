import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import ArticleDetail from './pages/ArticleDetail';
import VideoEditor from './pages/VideoEditor';
import { DashboardProvider } from './stores/DashboardContext';
import { HistoryProvider } from './stores/HistoryContext';

const queryClient = new QueryClient();

const phospheneTheme = {
  token: {
    colorPrimary: '#7C3AED',
    colorLink: '#7C3AED',
    borderRadius: 8,
    borderRadiusLG: 12,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBorder: '#EFE7FC',
    colorText: '#1E1B4B',
    colorTextSecondary: '#64748B',
    colorSuccess: '#10B981',
    colorWarning: '#F59E0B',
    colorError: '#EF4444',
    colorInfo: '#6366F1',
    boxShadow: '0 2px 12px rgba(124, 58, 237, 0.08)',
    boxShadowSecondary: '0 8px 24px rgba(124, 58, 237, 0.15)',
  },
  components: {
    Card: {
      boxShadow: '0 2px 12px rgba(124, 58, 237, 0.08)',
      boxShadowHover: '0 8px 24px rgba(124, 58, 237, 0.15)',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(124, 58, 237, 0.12)',
      itemHoverBg: 'rgba(124, 58, 237, 0.06)',
    },
    Button: {
      primaryShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
    },
    Tabs: {
      inkBarColor: '#7C3AED',
      itemSelectedColor: '#7C3AED',
      itemHoverColor: '#6366F1',
    },
  },
};

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={phospheneTheme}>
      <QueryClientProvider client={queryClient}>
        <DashboardProvider>
          <HistoryProvider>
            <BrowserRouter>
              <Routes>
                <Route element={<Layout />}>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/history/:id" element={<ArticleDetail />} />
                  <Route path="/video/:id" element={<VideoEditor />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </HistoryProvider>
        </DashboardProvider>
      </QueryClientProvider>
    </ConfigProvider>
  );
}
