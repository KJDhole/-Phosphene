import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Alert, Button, Progress, Skeleton, message } from 'antd';
import {
  ArrowLeftOutlined,
  CheckOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  fetchArticleDetail,
  generateVideo,
  getVideoStatus,
  getVideoUrl,
  type VideoStatusData,
} from '../api/client';

const renderStages = [
  { threshold: 0, label: '锁定脚本', meta: 'SCRIPT' },
  { threshold: 0.2, label: '生成配音', meta: 'VOICE' },
  { threshold: 0.5, label: '合成画面', meta: 'REMOTION' },
  { threshold: 0.9, label: '封装成片', meta: 'OUTPUT' },
];

export default function VideoEditor() {
  const { id: slug } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const category = searchParams.get('category') || undefined;
  const [videoStatus, setVideoStatus] = useState<VideoStatusData | null>(null);
  const [pollVersion, setPollVersion] = useState(0);
  const [starting, setStarting] = useState(false);

  const { data: article, isLoading: articleLoading, isError } = useQuery({
    queryKey: ['article', slug, category],
    queryFn: () => fetchArticleDetail(slug!, category),
    enabled: !!slug,
  });

  // Query once on entry so an existing output is shown. While rendering, use a
  // self-scheduling timeout: cleanup cancels the next request when the route exits.
  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const syncStatus = async () => {
      try {
        const next = await getVideoStatus(slug, category);
        if (cancelled) return;
        setVideoStatus(next);
        if (next.status === 'generating') {
          timer = setTimeout(syncStatus, 2000);
        }
      } catch {
        if (!cancelled) timer = setTimeout(syncStatus, 4000);
      }
    };

    void syncStatus();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [slug, category, pollVersion]);

  const videoScript = article?.formats?.video_script || '';
  const sceneCount = useMemo(() => {
    const headings = videoScript.match(/^#{2,3}\s+.+$/gm) || [];
    return headings.filter((heading) => !/脚本|说明|配置/.test(heading)).length;
  }, [videoScript]);
  const generating = videoStatus?.status === 'generating';
  const progress = Math.max(0, Math.min(100, Math.round((videoStatus?.progress || 0) * 100)));
  const videoBaseUrl = slug ? getVideoUrl(slug, article?.category) : '';
  const videoSrc = `${videoBaseUrl}${videoBaseUrl.includes('?') ? '&' : '?'}v=${pollVersion}`;

  const doGenerate = async () => {
    if (!slug || !article) return;
    setStarting(true);
    try {
      const next = await generateVideo(slug, article.category);
      setVideoStatus(next);
      setPollVersion((version) => version + 1);
      message.success('视频任务已进入渲染队列');
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || '无法启动视频生成';
      setVideoStatus({
        slug,
        status: 'failed',
        progress: 0,
        video_url: null,
        error: detail,
        message: null,
      });
      message.error(detail);
    } finally {
      setStarting(false);
    }
  };

  if (articleLoading) {
    return <div className="loading-sheet detail-loading"><Skeleton active paragraph={{ rows: 12 }} /></div>;
  }

  if (isError || !article) {
    return <Alert type="error" showIcon message="视频工作台加载失败" description="文章不存在，或文章数据暂时无法读取。" />;
  }

  return (
    <div className="video-studio-page page-enter">
      <header className="video-studio-header">
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/history/${article.slug}?category=${article.category}`)}>
          返回审核室
        </Button>
        <div className="video-studio-title">
          <span className="section-eyebrow">PHOSPHENE MOTION DESK</span>
          <h1>把文章变成一条片子</h1>
          <p>{article.title}</p>
        </div>
        <span className={`video-state state-${videoStatus?.status || 'pending'}`}>
          <i />{videoStatus?.status === 'done' ? '成片就绪' : generating ? '正在渲染' : videoStatus?.status === 'failed' ? '生成中断' : '等待生成'}
        </span>
      </header>

      <div className="video-studio-grid">
        <section className="script-sheet">
          <div className="studio-panel-heading">
            <div>
              <span className="section-eyebrow">01 / SOURCE</span>
              <h2>视频脚本</h2>
            </div>
            <div className="script-metrics">
              <span><b>{sceneCount || '—'}</b> 场景</span>
              <span><b>{videoScript.length}</b> 字符</span>
            </div>
          </div>
          {videoScript ? (
            <pre className="video-script-copy">{videoScript}</pre>
          ) : (
            <div className="video-script-empty">
              <VideoCameraOutlined />
              <strong>当前文章没有视频脚本</strong>
              <span>请先重新生成文章及其多格式内容。</span>
            </div>
          )}
        </section>

        <aside className="render-console">
          <div className="studio-panel-heading">
            <div>
              <span className="section-eyebrow">02 / RENDER</span>
              <h2>合成控制台</h2>
            </div>
            <strong className="render-percent">{progress}%</strong>
          </div>

          <Progress percent={progress} showInfo={false} strokeColor="#2457ff" trailColor="#dcd9d1" />
          <p className="render-message">
            {videoStatus?.message || (videoStatus?.status === 'done' ? '视频已经生成，可在下方预览。' : '脚本、配音与画面将在本地渲染流水线中完成。')}
          </p>

          <div className="render-stage-list">
            {renderStages.map((stage, index) => {
              const done = videoStatus?.status === 'done' || (videoStatus?.progress || 0) > stage.threshold;
              const active = generating && !done && index === renderStages.findIndex((item) => (videoStatus?.progress || 0) <= item.threshold);
              return (
                <div key={stage.meta} className={`${done ? 'done' : ''} ${active ? 'active' : ''}`}>
                  <span>{done ? <CheckOutlined /> : `0${index + 1}`}</span>
                  <strong>{stage.label}</strong>
                  <small>{stage.meta}</small>
                </div>
              );
            })}
          </div>

          {videoStatus?.status === 'failed' && (
            <Alert type="error" showIcon message="生成失败" description={videoStatus.error || '视频渲染进程异常终止'} />
          )}

          <Button
            type="primary"
            size="large"
            block
            icon={videoStatus?.status === 'done' ? <ReloadOutlined /> : <PlayCircleOutlined />}
            onClick={doGenerate}
            loading={starting || generating}
            disabled={!videoScript}
          >
            {generating ? '渲染进行中' : videoStatus?.status === 'done' ? '重新生成视频' : '开始生成视频'}
          </Button>

          <div className="render-specs">
            <span><small>ENGINE</small><b>Remotion</b></span>
            <span><small>VOICE</small><b>Config</b></span>
            <span><small>OUTPUT</small><b>MP4</b></span>
          </div>
        </aside>
      </div>

      {videoStatus?.status === 'done' && slug && (
        <section className="video-preview-section">
          <div className="studio-panel-heading">
            <div><span className="section-eyebrow">03 / OUTPUT</span><h2>成片预览</h2></div>
            <span className="output-ready"><CheckOutlined /> READY TO PLAY</span>
          </div>
          <video key={`${slug}-${pollVersion}`} controls preload="metadata">
            <source src={videoSrc} type="video/mp4" />
            当前浏览器不支持视频预览。
          </video>
        </section>
      )}
    </div>
  );
}
