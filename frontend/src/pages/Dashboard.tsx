import { useMemo, useState } from 'react';
import { Button, Drawer } from 'antd';
import {
  ArrowRightOutlined,
  CloseOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { fetchCategories, fetchHistory } from '../api/client';
import CategoryPicker from '../components/CategoryPicker';
import LogViewer from '../components/LogViewer';
import RunControls from '../components/RunControls';
import { useDashboard } from '../stores/DashboardContext';

const pipeline = [
  { id: 'collect', number: '01', title: '采集', caption: 'COLLECT', start: 0 },
  { id: 'evidence', number: '02', title: '证据整理', caption: 'GROUND', start: 0.28 },
  { id: 'write', number: '03', title: 'AI 写作', caption: 'GENERATE', start: 0.36 },
  { id: 'quality', number: '04', title: '质量校验', caption: 'VERIFY', start: 0.52 },
  { id: 'review', number: '05', title: '人工审核', caption: 'REVIEW', start: 0.86 },
  { id: 'publish', number: '06', title: '发布', caption: 'PUBLISH', start: 0.98 },
];

const categoryNames: Record<string, string> = {
  tech: '技术趋势', finance: '金融财经', business: '商业观察',
  entertainment: '娱乐文化', literature: '文学艺术', world: '国际新闻', zhongyi: '中医中药',
};

function statusForStage(index: number, progress: number, reviewPending: boolean, hasLogs: boolean) {
  if (!hasLogs) return 'waiting';
  if (reviewPending) {
    if (index < 4) return 'done';
    if (index === 4) return 'active';
    return 'waiting';
  }
  if (progress >= 1) return 'done';
  const next = pipeline[index + 1]?.start ?? 1.01;
  if (progress >= next) return 'done';
  if (progress >= pipeline[index].start) return 'active';
  return 'waiting';
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { selected, setSelected, isRunning, setIsRunning, runStatus, logs, clearLogs } = useDashboard();
  const { data: articles = [] } = useQuery({ queryKey: ['history'], queryFn: () => fetchHistory() });
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: fetchCategories });

  const pendingArticles = articles.filter((article) => (
    article.review_status === 'awaiting_review'
    || article.review_status === 'changes_requested'
    || (article.review_status === 'approved' && !article.deployment_ready)
  ));
  const issueArticles = articles.filter((article) => article.issue_count > 0 || !article.quality_passed);
  const rawLatestLog = logs[logs.length - 1];
  const currentCategory = runStatus.current_category || rawLatestLog?.category || selected[0] || '';
  const currentLogs = currentCategory ? logs.filter((entry) => entry.category === currentCategory) : logs;
  const latestLog = currentLogs[currentLogs.length - 1];
  const progress = currentLogs.reduce((max, entry) => Math.max(max, Number(entry.progress) || 0), 0);
  const reviewPending = currentLogs.some((entry) => entry.message.includes('等待人工审核'));
  const currentConfig = categories.find((category) => category.name === currentCategory);

  const evidenceCount = useMemo(() => {
    for (let index = currentLogs.length - 1; index >= 0; index -= 1) {
      const match = currentLogs[index].message.match(/获得\s*(\d+)\s*条有效证据/);
      if (match) return Number(match[1]);
    }
    return null;
  }, [currentLogs]);

  const dateTitle = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date()).replace(/\//g, '.');

  return (
    <div className="production-page">
      <section className="editorial-hero">
        <div>
          <span className="section-eyebrow">DAILY PRODUCTION / {dateTitle}</span>
          <h1>今日内容生产</h1>
          <p>把正在发生的事，变成有证据的表达。</p>
        </div>
        <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => setDrawerOpen(true)}>
          开始一次生产
        </Button>
      </section>

      <section className="pipeline-board" aria-label="内容生产流程">
        <div className="board-heading">
          <div>
            <span className="section-eyebrow">LIVE PIPELINE</span>
            <h2>{isRunning ? '当前生产正在流转' : reviewPending ? '内容已进入人工审核' : '生产流水线已就绪'}</h2>
          </div>
          <span className={`live-indicator ${isRunning ? 'active' : ''}`}>
            <i /> {isRunning ? 'LIVE' : (runStatus.status || 'idle').toUpperCase()}
          </span>
        </div>

        <div className="pipeline-track">
          {pipeline.map((stage, index) => {
            const status = statusForStage(index, progress, reviewPending, logs.length > 0 || isRunning);
            return (
              <div key={stage.id} className={`pipeline-stage ${status}`}>
                <div className="stage-rail"><i /></div>
                <span className="stage-number">{stage.number}</span>
                <strong>{stage.title}</strong>
                <small>{stage.caption}</small>
              </div>
            );
          })}
        </div>
      </section>

      <section className="workbench-grid">
        <article className="current-run-panel">
          <div className="panel-heading">
            <div>
              <span className="section-eyebrow">CURRENT RUN</span>
              <h2>{currentCategory ? categoryNames[currentCategory] || currentCategory : '尚未启动任务'}</h2>
            </div>
            <b>{Math.round(progress * 100).toString().padStart(2, '0')}%</b>
          </div>
          <div className="run-progress"><i style={{ width: `${Math.max(2, progress * 100)}%` }} /></div>
          <p className="run-message">{latestLog?.message || '选择内容分类，开始今天的第一次生产。'}</p>
          <div className="run-facts">
            <span><small>任务状态</small><strong>{runStatus.status}</strong></span>
            <span><small>当前信源</small><strong>{currentConfig?.sources.length ?? '—'}</strong></span>
            <span><small>有效证据</small><strong>{evidenceCount ?? '—'}</strong></span>
          </div>
          <LogViewer logs={logs} onClear={clearLogs} compact />
        </article>

        <aside className="evidence-snapshot">
          <div className="panel-heading compact-heading">
            <div>
              <span className="section-eyebrow">SOURCE FIELD</span>
              <h2>信源现场</h2>
            </div>
            <span>{currentConfig?.sources.length || 0} SOURCES</span>
          </div>
          <div className="source-list">
            {(currentConfig?.sources || []).slice(0, 6).map((source, index) => (
              <div key={`${source.name}-${index}`}>
                <span className={`source-type type-${source.type}`}>{source.type.toUpperCase()}</span>
                <strong>{source.display_name}</strong>
                <i className={isRunning ? 'collecting' : ''} />
              </div>
            ))}
            {!currentConfig && <p className="empty-note">启动任务后，这里会展示正在使用的真实信源。</p>}
          </div>
        </aside>
      </section>

      <section className="attention-section">
        <div className="section-title-row">
          <div>
            <span className="section-eyebrow">NEEDS ATTENTION</span>
            <h2>待你处理</h2>
          </div>
          <Button type="link" onClick={() => navigate('/review')}>进入审核室 <ArrowRightOutlined /></Button>
        </div>
        <div className="attention-summary">
          <div><strong>{String(pendingArticles.length).padStart(2, '0')}</strong><span>待审核文章</span></div>
          <div><strong>{String(issueArticles.length).padStart(2, '0')}</strong><span>需要复核</span></div>
          <div><strong>{String(articles.filter((article) => article.deployment_ready).length).padStart(2, '0')}</strong><span>已审核通过</span></div>
        </div>
        <div className="attention-list">
          {pendingArticles.slice(0, 3).map((article) => (
            <button key={`${article.category}-${article.slug}`} onClick={() => navigate(`/history/${article.slug}?category=${article.category}&from=review`)}>
              <span>{categoryNames[article.category] || article.category}</span>
              <strong>{article.title}</strong>
              <small>{article.evidence_count} 条证据 · {article.issue_count ? `${article.issue_count} 项提醒` : '质量校验通过'}</small>
              <ArrowRightOutlined />
            </button>
          ))}
          {pendingArticles.length === 0 && <p className="empty-note">目前没有待审核内容。新文章通过质量校验后会出现在这里。</p>}
        </div>
      </section>

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={720}
        closeIcon={<CloseOutlined />}
        title={null}
        className="production-drawer"
      >
        <div className="drawer-intro">
          <span className="section-eyebrow">NEW PRODUCTION</span>
          <h2>选择今天要追踪的方向</h2>
          <p>每个分类会独立采集证据、生成内容并进入审核队列。</p>
        </div>
        <CategoryPicker selected={selected} onChange={setSelected} />
        <RunControls
          selected={selected}
          isRunning={isRunning}
          onBeforeRun={clearLogs}
          onRunStart={() => {
            setIsRunning(true);
            setDrawerOpen(false);
          }}
        />
      </Drawer>
    </div>
  );
}
