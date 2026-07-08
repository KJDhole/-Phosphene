import { useState, useEffect } from 'react';
import { Button, Space } from 'antd';
import {
  ArrowLeftOutlined,
  CopyOutlined,
  DownloadOutlined,
  VerticalAlignTopOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

interface Props {
  title: string;
  onCopy: () => void;
  onDownload: () => void;
  /** 触发显示的滚动阈值（px），默认 300 */
  threshold?: number;
}

/**
 * 浮动底部操作栏
 *
 * 固定在视口底部，滚动超过阈值后滑入显示。
 * 包含：返回 / 标题 / 复制 / 下载 / 回到顶部。
 * z-index 设在 50，低于 Layout Header(100) 但高于普通内容，
 * 避免被其他毛玻璃元素遮挡。
 */
export default function ArticleBottomBar({
  title,
  onCopy,
  onDownload,
  threshold = 300,
}: Props) {
  const navigate = useNavigate();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setVisible(window.scrollY > threshold);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // 初始化检查
    return () => window.removeEventListener('scroll', handleScroll);
  }, [threshold]);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 220, /* Sidebar 宽度 */
        right: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 28px',
        gap: 12,
        minHeight: 56,

        /* Glassmorphism */
        background: 'rgba(255, 255, 255, 0.78)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderTop: '1px solid rgba(239, 231, 252, 0.8)',
        boxShadow: '0 -4px 24px rgba(124, 58, 237, 0.1)',

        /* 动画 */
        transition: 'transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease',
        transform: visible ? 'translateY(0)' : 'translateY(100%)',
        opacity: visible ? 1 : 0,
        pointerEvents: visible ? 'auto' as const : 'none' as const,
      }}
    >
      {/* 左侧：返回 */}
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/history')}
        style={{
          borderColor: '#EFE7FC',
          color: '#64748B',
          borderRadius: 8,
          flexShrink: 0,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
        }}
      >
        返回
      </Button>

      {/* 中间：文章标题（截断） */}
      <span
        style={{
          flex: 1,
          minWidth: 0,
          fontSize: 14,
          fontWeight: 500,
          color: '#1E1B4B',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          textAlign: 'center',
          padding: '0 8px',
          lineHeight: '20px',
        }}
        title={title}
      >
        {title}
      </span>

      {/* 右侧：操作按钮 */}
      <Space size={8} style={{ flexShrink: 0 }}>
        <Button
          icon={<CopyOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onCopy();
          }}
          size="small"
          style={{
            borderColor: '#EFE7FC',
            color: '#7C3AED',
            borderRadius: 8,
          }}
          title="复制内容"
        />
        <Button
          icon={<DownloadOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onDownload();
          }}
          size="small"
          type="primary"
          style={{
            background: 'linear-gradient(135deg, #7C3AED 0%, #6366F1 100%)',
            border: 'none',
            borderRadius: 8,
          }}
          title="下载 .md"
        />
        <Button
          icon={<VerticalAlignTopOutlined />}
          onClick={scrollToTop}
          size="small"
          style={{
            borderColor: '#EFE7FC',
            color: '#94A3B8',
            borderRadius: 8,
          }}
          title="回到顶部"
        />
      </Space>
    </div>
  );
}
