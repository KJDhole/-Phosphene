import { Tag, Space, Button, Popconfirm, message, Tooltip } from 'antd';
import { EyeOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteArticle, runCategory } from '../api/client';
import type { ArticleSummary } from '../api/client';

interface Props {
  article: ArticleSummary;
}

const formatLabels: Record<string, { label: string; color: string }> = {
  blog: { label: '博客', color: '#7C3AED' },
  twitter: { label: '推文', color: '#1DA1F2' },
  newsletter: { label: '通讯', color: '#10B981' },
  video_script: { label: '脚本', color: '#F59E0B' },
  english: { label: 'EN', color: '#EC4899' },
};

const categoryColors: Record<string, string> = {
  tech: '#7C3AED',
  finance: '#10B981',
  business: '#6366F1',
  entertainment: '#EC4899',
  literature: '#F59E0B',
  world: '#3B82F6',
  zhongyi: '#059669',
};

export default function ArticleCard({ article }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => deleteArticle(article.slug, article.category),
    onSuccess: () => {
      message.success('已删除');
      queryClient.invalidateQueries({ queryKey: ['history'] });
    },
    onError: () => message.error('删除失败'),
  });

  const rerunMutation = useMutation({
    mutationFn: () => runCategory(article.category),
    onSuccess: () => message.success('已启动重新生成'),
  });

  const accentColor = categoryColors[article.category] || '#7C3AED';

  return (
    <div
      className="article-card"
      style={{
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: 16,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <Space style={{ marginBottom: 8 }}>
          <Tag style={{
            background: `${accentColor}12`,
            color: accentColor,
            border: `1px solid ${accentColor}25`,
            borderRadius: 4,
            fontWeight: 600,
            fontSize: 11,
            padding: '0 8px',
            lineHeight: '22px',
          }}>
            {article.category}
          </Tag>
          <span style={{ color: '#94A3B8', fontSize: 12 }}>{article.date}</span>
        </Space>
        <div style={{
          fontSize: 16,
          fontWeight: 600,
          color: '#1E1B4B',
          marginBottom: 8,
          lineHeight: 1.4,
        }}>
          {article.title}
        </div>
        <Space size={6} style={{ flexWrap: 'wrap' }}>
          {article.formats.map((fmt) => {
            const info = formatLabels[fmt] || { label: fmt, color: '#64748B' };
            return (
              <Tag
                key={fmt}
                style={{
                  background: `${info.color}10`,
                  color: info.color,
                  border: `1px solid ${info.color}25`,
                  borderRadius: 4,
                  fontSize: 11,
                  lineHeight: '20px',
                }}
              >
                {info.label}
              </Tag>
            );
          })}
        </Space>
      </div>

      <Space style={{ flexShrink: 0 }}>
        <Tooltip title="预览">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/history/${article.slug}?category=${article.category}`)}
            style={{ color: '#64748B' }}
          >
            预览
          </Button>
        </Tooltip>
        <Tooltip title="重新生成">
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={rerunMutation.isPending}
            onClick={() => rerunMutation.mutate()}
            style={{ color: '#64748B' }}
          />
        </Tooltip>
        <Popconfirm title="确定删除？" onConfirm={() => deleteMutation.mutate()}>
          <Tooltip title="删除">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Tooltip>
        </Popconfirm>
      </Space>
    </div>
  );
}
