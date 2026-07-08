import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Card,
  Button,
  Progress,
  Typography,
  Alert,
  Spin,
  Space,
  Divider,
} from 'antd';
import {
  VideoCameraOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchArticleDetail, generateVideo, getVideoStatus, getVideoUrl } from '../api/client';

const { Title, Text } = Typography;

export default function VideoEditor() {
  const { id: slug } = useParams<{ id: string }>();
  const category = new URLSearchParams(window.location.search).get('category') || undefined;

  const [generating, setGenerating] = useState(false);
  const [videoStatus, setVideoStatus] = useState<any>(null);

  // 获取文章详情
  const { data: article, isLoading: articleLoading } = useQuery({
    queryKey: ['article', slug, category],
    queryFn: () => fetchArticleDetail(slug!, category),
    enabled: !!slug,
  });

  const doGenerate = async () => {
    if (!slug) return;
    setGenerating(true);
    setVideoStatus({ status: 'generating', progress: 0 });
    try {
      const status = await generateVideo(slug, category || 'tech');
      setVideoStatus(status);
      // 轮询进度
      const timer = setInterval(async () => {
        try {
          const s = await getVideoStatus(slug, category);
          setVideoStatus(s);
          if (s.status === 'done' || s.status === 'failed') {
            clearInterval(timer);
            setGenerating(false);
          }
        } catch { /* ignore */ }
      }, 2000);
    } catch (e: any) {
      setVideoStatus({ status: 'failed', error: e.message });
      setGenerating(false);
    }
  };

  // 清理轮询
  useEffect(() => {
    return () => {
      setVideoStatus(null);
    };
  }, [slug]);

  const videoScript = article?.formats?.['video_script'] || '';

  return (
    <div>
      <Title level={4} style={{ fontWeight: 600 }}>
        🎬 视频生成
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginTop: 0 }}>视频脚本预览</Title>
        {articleLoading ? (
          <Spin />
        ) : videoScript ? (
          <pre style={{
            background: '#f8f7fc',
            padding: 16,
            borderRadius: 8,
            fontSize: 14,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
            maxHeight: 400,
            overflow: 'auto',
          }}>
            {videoScript}
          </pre>
        ) : (
          <Text type="secondary">暂无视频脚本，请先生成文章</Text>
        )}
      </Card>

      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Button
            type="primary"
            icon={<VideoCameraOutlined />}
            size="large"
            onClick={doGenerate}
            loading={generating}
            disabled={!videoScript}
            style={{ borderRadius: 8, height: 44, paddingInline: 32 }}
          >
            {generating ? '生成中...' : '▶ 生成视频'}
          </Button>

          {videoStatus?.status === 'generating' && (
            <div>
              <Text>正在生成视频...</Text>
              <Progress
                percent={Math.round((videoStatus.progress || 0) * 100)}
                status="active"
                strokeColor="#7C3AED"
              />
            </div>
          )}

          {videoStatus?.status === 'done' && slug && (
            <div>
              <Alert
                type="success"
                message="视频生成完成！"
                showIcon
                style={{ borderRadius: 8, marginBottom: 12 }}
              />
              <video
                controls
                style={{
                  width: '100%',
                  maxHeight: 400,
                  borderRadius: 8,
                  background: '#000',
                }}
              >
                <source src={getVideoUrl(slug, category)} type="video/mp4" />
              </video>
            </div>
          )}

          {videoStatus?.status === 'failed' && (
            <Alert
              type="error"
              message="生成失败"
              description={videoStatus.error || '未知错误'}
              showIcon
              style={{ borderRadius: 8 }}
            />
          )}
        </Space>
      </Card>

      {/* ✅ 预留 — v2 配置编辑区 */}
      <Divider />
      <Card
        title="⚙️ 高级配置（下版本开放）"
        style={{ opacity: 0.5 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: 16, textAlign: 'center', color: '#999' }}>
            📝 Prompt 编辑 — 可自定义视频脚本生成提示词
          </div>
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: 16, textAlign: 'center', color: '#999' }}>
            🔧 场景微调 — 可逐场景编辑文案、视觉类型、配色
          </div>
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: 16, textAlign: 'center', color: '#999' }}>
            🎚️ 流程配置 — 可设置默认配音、分辨率、帧率等参数
          </div>
        </Space>
      </Card>
    </div>
  );
}
