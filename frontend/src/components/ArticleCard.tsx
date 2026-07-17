import { Button, Popconfirm, Tooltip, message } from 'antd';
import { ArrowRightOutlined, DeleteOutlined, ReloadOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { deleteArticle, runCategory, type ArticleSummary, type ReviewStatus } from '../api/client';

const categoryMeta: Record<string, { label: string; index: string }> = {
  tech: { label: '技术趋势', index: 'TEC' },
  finance: { label: '金融财经', index: 'FIN' },
  business: { label: '商业观察', index: 'BUS' },
  entertainment: { label: '娱乐文化', index: 'ENT' },
  literature: { label: '文学艺术', index: 'LIT' },
  world: { label: '国际新闻', index: 'WLD' },
  zhongyi: { label: '中医中药', index: 'TCM' },
};

const statusMeta: Record<ReviewStatus, { label: string; className: string }> = {
  awaiting_review: { label: '待审核', className: 'waiting' },
  changes_requested: { label: '需修改', className: 'changes' },
  approved: { label: '已通过', className: 'approved' },
  not_required: { label: '无需审核', className: 'neutral' },
  legacy_unverified: { label: '旧版未验证', className: 'legacy' },
};

export default function ArticleCard({ article, reviewMode = false }: { article: ArticleSummary; reviewMode?: boolean }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const category = categoryMeta[article.category] || { label: article.category, index: 'ETC' };
  const status = article.review_status === 'approved' && !article.deployment_ready
    ? { label: '审核已失效', className: 'changes' }
    : statusMeta[article.review_status] || statusMeta.legacy_unverified;
  const detailUrl = `/history/${article.slug}?category=${article.category}${reviewMode ? '&from=review' : ''}`;

  const deleteMutation = useMutation({
    mutationFn: () => deleteArticle(article.slug, article.category),
    onSuccess: () => {
      message.success('文章已删除');
      queryClient.invalidateQueries({ queryKey: ['history'] });
    },
    onError: () => message.error('删除失败'),
  });
  const rerunMutation = useMutation({
    mutationFn: () => runCategory(article.category),
    onSuccess: () => message.success('重新生成任务已启动'),
    onError: (error: any) => message.error(error?.response?.data?.detail || '启动失败'),
  });

  return (
    <article className="archive-row">
      <div className="archive-date">
        <strong>{article.date.slice(8, 10) || '—'}</strong>
        <span>{article.date.slice(0, 7).replace('-', '.')}</span>
      </div>
      <div className="archive-category">
        <span>{category.index}</span>
        <strong>{category.label}</strong>
      </div>
      <button className="archive-main" onClick={() => navigate(detailUrl)}>
        <span className={`review-status ${status.className}`}><i />{status.label}</span>
        <h3>{article.title}</h3>
        <p>
          {article.evidence_count} 条证据
          <i />
          {article.formats.length} 种内容格式
          <i />
          {article.issue_count ? `${article.issue_count} 项提醒` : '无质量提醒'}
        </p>
      </button>
      <div className="archive-actions">
        {!reviewMode && (
          <Tooltip title="生成视频">
            <Button type="text" icon={<VideoCameraOutlined />} onClick={() => navigate(`/video/${article.slug}?category=${article.category}`)} />
          </Tooltip>
        )}
        <Tooltip title="重新生成">
          <Button type="text" icon={<ReloadOutlined />} loading={rerunMutation.isPending} onClick={() => rerunMutation.mutate()} />
        </Tooltip>
        {!reviewMode && (
          <Popconfirm title="确定删除这篇文章？" onConfirm={() => deleteMutation.mutate()}>
            <Tooltip title="删除"><Button type="text" danger icon={<DeleteOutlined />} /></Tooltip>
          </Popconfirm>
        )}
        <Button className="open-article" icon={<ArrowRightOutlined />} onClick={() => navigate(detailUrl)} aria-label="打开文章" />
      </div>
    </article>
  );
}
