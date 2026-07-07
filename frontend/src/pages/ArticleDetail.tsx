import { useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Button, Space, message, Skeleton, Typography } from 'antd';
import { ArrowLeftOutlined, CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchArticleDetail } from '../api/client';
import FormatTabs from '../components/FormatTabs';

const { Title } = Typography;

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const category = searchParams.get('category') || undefined;
  const [activeFormat, setActiveFormat] = useState('blog');

  const { data: article, isLoading } = useQuery({
    queryKey: ['article', id, category],
    queryFn: () => fetchArticleDetail(id!, category),
    enabled: !!id,
  });

  const handleCopy = () => {
    if (!article) return;
    const content = article.formats[activeFormat];
    if (content) {
      navigator.clipboard.writeText(content);
      message.success('已复制到剪贴板');
    }
  };

  const handleDownload = () => {
    if (!article) return;
    const content = article.formats[activeFormat];
    if (content) {
      const blob = new Blob([content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${article.slug}_${activeFormat}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (isLoading) {
    return (
      <div className="glass" style={{ padding: 24, borderRadius: 12 }}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    );
  }

  if (!article) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: '#64748B' }}>
        文章不存在
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 20,
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/history')}
            style={{
              borderColor: '#EFE7FC',
              color: '#64748B',
            }}
          >
            返回
          </Button>
          <Title level={4} style={{ margin: 0, fontWeight: 600 }}>
            {article.title}
          </Title>
        </Space>

        <Space>
          <Button
            icon={<CopyOutlined />}
            onClick={handleCopy}
            style={{
              borderColor: '#7C3AED',
              color: '#7C3AED',
            }}
          >
            复制
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownload}
            type="primary"
            style={{
              background: 'linear-gradient(135deg, #7C3AED 0%, #6366F1 100%)',
              border: 'none',
              boxShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
            }}
          >
            下载 .md
          </Button>
        </Space>
      </div>

      {/* Format Tabs */}
      <FormatTabs
        formats={article.formats}
        activeKey={activeFormat}
        onChange={setActiveFormat}
      />
    </div>
  );
}
