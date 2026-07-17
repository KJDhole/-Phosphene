import { useMemo, useState } from 'react';
import { Empty, Segmented, Skeleton } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { fetchHistory, type ArticleSummary } from '../api/client';
import ArticleCard from '../components/ArticleCard';

type QueueFilter = '待审核' | '需修改' | '已通过' | '旧版内容';

function matches(article: ArticleSummary, filter: QueueFilter) {
  if (filter === '待审核') return article.review_status === 'awaiting_review';
  if (filter === '需修改') return article.review_status === 'changes_requested' || (article.review_status === 'approved' && !article.deployment_ready);
  if (filter === '已通过') return article.review_status === 'approved' && article.deployment_ready;
  return article.review_status === 'legacy_unverified';
}

export default function ReviewQueue() {
  const [filter, setFilter] = useState<QueueFilter>('待审核');
  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => fetchHistory(),
  });
  const visible = useMemo(() => articles.filter((article) => matches(article, filter)), [articles, filter]);
  const pending = articles.filter((article) => article.review_status === 'awaiting_review').length;
  const changes = articles.filter((article) => article.review_status === 'changes_requested' || (article.review_status === 'approved' && !article.deployment_ready)).length;
  const passed = articles.filter((article) => article.review_status === 'approved' && article.deployment_ready).length;

  return (
    <div className="review-queue-page">
      <section className="page-heading editorial-heading">
        <div>
          <span className="section-eyebrow">HUMAN REVIEW DESK</span>
          <h1>内容审核</h1>
          <p>AI 负责生成，你负责最后的判断。</p>
        </div>
        <div className="review-count-mark">
          <strong>{String(pending).padStart(2, '0')}</strong>
          <span>WAITING<br />FOR YOU</span>
        </div>
      </section>

      <section className="review-stats">
        <div><span>01</span><strong>{pending}</strong><small>待你审核</small></div>
        <div><span>02</span><strong>{changes}</strong><small>已退回修改</small></div>
        <div><span>03</span><strong>{passed}</strong><small>已通过审核</small></div>
        <div><span>04</span><strong>{articles.filter((article) => article.issue_count > 0).length}</strong><small>含质量提醒</small></div>
      </section>

      <div className="queue-toolbar">
        <Segmented
          value={filter}
          onChange={(value) => setFilter(value as QueueFilter)}
          options={['待审核', '需修改', '已通过', '旧版内容']}
        />
        <span>{visible.length} ITEMS</span>
      </div>

      <section className="archive-list review-list">
        {isLoading ? (
          <div className="loading-sheet"><Skeleton active paragraph={{ rows: 7 }} /></div>
        ) : visible.length ? visible.map((article) => (
          <ArticleCard key={`${article.category}-${article.slug}`} article={article} reviewMode />
        )) : (
          <div className="editorial-empty">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`暂无“${filter}”内容`} />
          </div>
        )}
      </section>
    </div>
  );
}
