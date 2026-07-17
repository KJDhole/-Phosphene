import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import { DashboardProvider } from './stores/DashboardContext';
import { HistoryProvider } from './stores/HistoryContext';

const queryClient = new QueryClient();
const Dashboard = lazy(() => import('./pages/Dashboard'));
const History = lazy(() => import('./pages/History'));
const ArticleDetail = lazy(() => import('./pages/ArticleDetail'));
const VideoEditor = lazy(() => import('./pages/VideoEditor'));
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'));

function Page({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="route-loading"><i /><span>正在打开工作台…</span></div>}>{children}</Suspense>;
}

const phospheneTheme = {
  token: {
    colorPrimary: '#2457FF',
    colorLink: '#2457FF',
    borderRadius: 6,
    borderRadiusLG: 10,
    fontFamily: "'MiSans', 'Inter', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif",
    colorBgContainer: '#FCFBF8',
    colorBgElevated: '#FCFBF8',
    colorBorder: '#DCD9D1',
    colorText: '#12151C',
    colorTextSecondary: '#686B73',
    colorSuccess: '#4F7B17',
    colorWarning: '#C86A24',
    colorError: '#D7462F',
    colorInfo: '#2457FF',
    boxShadow: '0 1px 2px rgba(18, 21, 28, 0.05)',
    boxShadowSecondary: '0 16px 40px rgba(18, 21, 28, 0.12)',
  },
  components: {
    Card: {
      boxShadow: 'none',
      boxShadowHover: 'none',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#12151C',
      itemSelectedColor: '#FCFBF8',
      itemHoverBg: '#ECE9E2',
    },
    Button: {
      primaryShadow: 'none',
    },
    Tabs: {
      inkBarColor: '#2457FF',
      itemSelectedColor: '#12151C',
      itemHoverColor: '#2457FF',
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
                  <Route path="/" element={<Page><Dashboard /></Page>} />
                  <Route path="/history" element={<Page><History /></Page>} />
                  <Route path="/review" element={<Page><ReviewQueue /></Page>} />
                  <Route path="/history/:id" element={<Page><ArticleDetail /></Page>} />
                  <Route path="/video/:id" element={<Page><VideoEditor /></Page>} />
                </Route>
              </Routes>
            </BrowserRouter>
          </HistoryProvider>
        </DashboardProvider>
      </QueryClientProvider>
    </ConfigProvider>
  );
}
