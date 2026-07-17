import { useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Input,
  Modal,
  Skeleton,
  Tooltip,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckOutlined,
  CopyOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchArticleDetail,
  runCategory,
  updateArticleReview,
  type EvidenceItem,
} from '../api/client';
import MarkdownRenderer from '../components/MarkdownRenderer';

const formatLabels: Record<string, string> = {
  blog: '中文博客', twitter: '社交短文', newsletter: 'Newsletter',
  video_script: '视频脚本', english: 'English',
};

const statusLabels: Record<string, string> = {
  awaiting_review: '等待人工审核', changes_requested: '已退回修改',
  approved: '已通过审核', not_required: '无需审核', legacy_unverified: '旧版内容未验证',
};

function evidenceDomId(sourceId: string) {
  return `evidence-card-${sourceId.replace(':', '--')}`;
}

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const category = searchParams.get('category') || undefined;
  const fromReview = searchParams.get('from') === 'review';
  const [activeFormat, setActiveFormat] = useState('blog');
  const [selectedEvidence, setSelectedEvidence] = useState<string | null>(null);
  const [changesOpen, setChangesOpen] = useState(false);
  const [reviewNote, setReviewNote] = useState('');

  const { data: article, isLoading, isError, error } = useQuery({
    queryKey: ['article', id, category],
    queryFn: () => fetchArticleDetail(id!, category),
    enabled: !!id,
  });

  const knownCitationIds = useMemo(
    () => new Set((article?.evidence || []).map((item) => item.source_id)),
    [article?.evidence],
  );
  const articleCitations = useMemo(() => {
    const blog = article?.formats.blog || '';
    return Array.from(new Set(Array.from(
      blog.matchAll(/\[(?:证据(?:编号)?\s*[:：]?\s*)?([\w-]+)\s*[:：]\s*(\d+)\]/g),
      (match) => `${match[1]}:${match[2]}`,
    )));
  }, [article?.formats.blog]);
  const unknownCitations = articleCitations.filter((citation) => !knownCitationIds.has(citation));

  const reviewMutation = useMutation({
    mutationFn: ({ status, note }: { status: 'approved' | 'changes_requested'; note: string }) => (
      updateArticleReview(article!.slug, article!.category, status, note)
    ),
    onSuccess: (updated) => {
      queryClient.setQueryData(['article', id, category], updated);
      queryClient.invalidateQueries({ queryKey: ['history'] });
      setChangesOpen(false);
      setReviewNote('');
      message.success(updated.review_status === 'approved' ? '审核已通过，文章可进入部署' : '已退回修改');
    },
    onError: (mutationError: any) => message.error(mutationError?.response?.data?.detail || '审核状态更新失败'),
  });

  const rerunMutation = useMutation({
    mutationFn: () => runCategory(article!.category),
    onSuccess: () => message.success('重新生成任务已启动'),
    onError: (mutationError: any) => message.error(mutationError?.response?.data?.detail || '启动失败'),
  });

  const locateEvidence = (sourceId: string) => {
    setSelectedEvidence(sourceId);
    window.setTimeout(() => {
      document.getElementById(evidenceDomId(sourceId))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 0);
  };

  const copyContent = async () => {
    const content = article?.formats[activeFormat];
    if (!content) return;
    await navigator.clipboard.writeText(content);
    message.success('已复制当前内容');
  };

  const downloadContent = () => {
    const content = article?.formats[activeFormat];
    if (!article || !content) return;
    const url = URL.createObjectURL(new Blob([content], { type: 'text/markdown' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${article.category}_${article.slug}_${activeFormat}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) return <div className="loading-sheet detail-loading"><Skeleton active paragraph={{ rows: 14 }} /></div>;
  if (isError || !article) {
    return <Alert type="error" showIcon message="文章加载失败" description={(error as any)?.response?.data?.detail || '文章不存在或已被移除'} />;
  }

  const quality = article.quality || {};
  const evidence = article.evidence || [];
  const canApprove = quality.passed === true && unknownCitations.length === 0 && !article.deployment_ready;
  const displayedStatus = article.review_status === 'approved' && !article.deployment_ready
    ? '审核已失效，需重新确认'
    : statusLabels[article.review_status] || article.review_status;

  return (
    <div className="review-room-page">
      <header className="review-room-header">
        <div className="review-title-row">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(fromReview ? '/review' : '/history')}>
            {fromReview ? '返回审核队列' : '返回内容档案'}
          </Button>
          <span className={`review-status-large status-${article.review_status}`}><i />{displayedStatus}</span>
        </div>
        <div className="review-document-title">
          <span>{article.category.toUpperCase()} / {article.date}</span>
          <h1>{article.title}</h1>
        </div>
        <div className="document-tools">
          <Tooltip title="复制"><Button type="text" icon={<CopyOutlined />} onClick={copyContent} /></Tooltip>
          <Tooltip title="下载 Markdown"><Button type="text" icon={<DownloadOutlined />} onClick={downloadContent} /></Tooltip>
          <Button type="text" icon={<VideoCameraOutlined />} onClick={() => navigate(`/video/${article.slug}?category=${article.category}`)}>视频</Button>
        </div>
      </header>

      <nav className="format-switcher" aria-label="内容格式">
        {Object.keys(article.formats).map((format, index) => (
          <button key={format} className={activeFormat === format ? 'active' : ''} onClick={() => setActiveFormat(format)}>
            <span>0{index + 1}</span>{formatLabels[format] || format}
          </button>
        ))}
      </nav>

      {activeFormat === 'blog' ? (
        <div className="review-room-grid">
          <main className="article-canvas">
            <div className="article-canvas-label"><span>DOCUMENT</span><b>MARKDOWN / ZH-CN</b></div>
            <MarkdownRenderer content={article.formats.blog || ''} knownCitationIds={knownCitationIds} onCitationClick={locateEvidence} />
          </main>

          <aside className="evidence-dock">
            <div className="dock-heading">
              <div><span className="section-eyebrow">TRACEABLE SOURCES</span><h2>引用证据</h2></div>
              <strong>{evidence.length}</strong>
            </div>
            {evidence.length ? evidence.map((item: EvidenceItem) => (
              <article
                id={evidenceDomId(item.source_id)}
                key={item.source_id}
                className={`evidence-card ${selectedEvidence === item.source_id ? 'selected' : ''} ${articleCitations.includes(item.source_id) ? 'cited' : ''}`}
                onClick={() => setSelectedEvidence(item.source_id)}
              >
                <div className="evidence-card-top">
                  <code>{item.source_id}</code>
                  <span>{articleCitations.includes(item.source_id) ? '已引用' : '未使用'}</span>
                </div>
                <h3>{item.title}</h3>
                {item.summary && <p>{item.summary}</p>}
                <div className="evidence-card-meta">
                  <span>{item.source_display_name || item.source_name}</span>
                  {item.published_at && <time>{item.published_at.slice(0, 10)}</time>}
                </div>
                <a href={item.url} target="_blank" rel="noopener noreferrer" onClick={(event) => event.stopPropagation()}>
                  打开原始页面 <LinkOutlined />
                </a>
              </article>
            )) : <p className="empty-note">这是旧版文章，没有可追溯证据。请重新生成后再审核。</p>}
          </aside>

          <aside className="quality-inspector">
            <div className="dock-heading">
              <div><span className="section-eyebrow">QUALITY GATE</span><h2>质量检查</h2></div>
            </div>
            <div className={`quality-verdict ${quality.passed ? 'passed' : 'blocked'}`}>
              {quality.passed ? <CheckOutlined /> : <ExclamationCircleOutlined />}
              <div><strong>{quality.passed ? '可进入审核' : '尚不可通过'}</strong><span>{quality.passed ? '自动校验已通过' : '需要修复质量问题'}</span></div>
            </div>
            <div className="quality-metrics">
              <div><span>证据总数</span><strong>{quality.evidence_count ?? evidence.length}</strong></div>
              <div><span>实际引用</span><strong>{quality.cited_sources?.length ?? articleCitations.length}</strong></div>
              <div><span>无效引用</span><strong className={unknownCitations.length ? 'danger' : ''}>{unknownCitations.length}</strong></div>
            </div>
            {unknownCitations.length > 0 && (
              <div className="quality-issue error"><strong>引用编号不存在</strong><p>{unknownCitations.join(', ')}</p></div>
            )}
            {quality.errors?.map((item) => <div className="quality-issue error" key={item}><strong>必须修复</strong><p>{item}</p></div>)}
            {quality.warnings?.map((item) => <div className="quality-issue warning" key={item}><strong>人工确认</strong><p>{item}</p></div>)}
            {article.review_note && <div className="review-note"><span>上次审核意见</span><p>{article.review_note}</p></div>}
          </aside>
        </div>
      ) : (
        <main className="article-canvas standalone-format">
          <div className="article-canvas-label"><span>{formatLabels[activeFormat] || activeFormat}</span><b>DERIVED CONTENT</b></div>
          <MarkdownRenderer content={article.formats[activeFormat] || ''} />
        </main>
      )}

      <footer className="review-action-bar">
        <div>
          <span>当前决策</span>
          <strong>{displayedStatus}</strong>
        </div>
        <div className="review-actions">
          {article.review_status === 'legacy_unverified' ? (
            <Button icon={<ReloadOutlined />} loading={rerunMutation.isPending} onClick={() => rerunMutation.mutate()}>重新生成后审核</Button>
          ) : (
            <>
              <Button onClick={() => setChangesOpen(true)} disabled={reviewMutation.isPending}>退回修改</Button>
              <Tooltip title={!canApprove ? '只有通过质量校验且引用完整的文章可以通过' : ''}>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  disabled={!canApprove}
                  loading={reviewMutation.isPending}
                  onClick={() => reviewMutation.mutate({ status: 'approved', note: '' })}
                >审核通过</Button>
              </Tooltip>
            </>
          )}
        </div>
      </footer>

      <Modal
        open={changesOpen}
        title="退回修改"
        okText="确认退回"
        cancelText="取消"
        okButtonProps={{ danger: true, disabled: !reviewNote.trim(), loading: reviewMutation.isPending }}
        onCancel={() => setChangesOpen(false)}
        onOk={() => reviewMutation.mutate({ status: 'changes_requested', note: reviewNote })}
      >
        <p>写下明确的修改意见，便于后续人工或 AI 处理。</p>
        <Input.TextArea rows={5} maxLength={1000} showCount value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="例如：第三段对数据的解读超出了证据范围，请删除或补充来源。" />
      </Modal>
    </div>
  );
}
