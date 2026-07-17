import { useState, useEffect, useCallback } from 'react';
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
 *
 * ## z-index 策略
 * - Layout Header: 100（最顶层，含操作按钮）
 * - 本组件:       80（介于 Header 与内容之间）
 * - 侧边栏:       auto（正常流）
 * - 普通内容:     auto
 *
 * 使用 isolation: isolate 创建独立堆叠上下文，
 * 采用高对比深色工具条，与审核室底部操作区保持一致。
 */
export default function ArticleBottomBar({
  title,
  onCopy,
  onDownload,
  threshold = 300,
}: Props) {
  const navigate = useNavigate();
  const [visible, setVisible] = useState(false);
  const [atBottom, setAtBottom] = useState(false);

  const handleScroll = useCallback(() => {
    const scrollY = window.scrollY;
    setVisible(scrollY > threshold);
    // 检测是否接近底部（用于决定是否显示「回到顶部」提示）
    const docHeight = document.documentElement.scrollHeight;
    const winHeight = window.innerHeight;
    setAtBottom(scrollY + winHeight >= docHeight - 60);
  }, [threshold]);

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const goBack = useCallback(() => {
    navigate('/history');
  }, [navigate]);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 'calc(var(--sidebar) + 48px)',
        right: 48,
        zIndex: 80,
        isolation: 'isolate',
        willChange: 'transform',

        /* 布局 */
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 28px',
        gap: 12,
        minHeight: 56,

        background: 'rgba(18, 21, 28, 0.96)',
        color: '#FCFBF8',
        border: '1px solid #343943',
        boxShadow: '0 18px 50px rgba(18, 21, 28, 0.24)',

        /* 滑入动画 */
        transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease',
        transform: visible ? 'translateY(0)' : 'translateY(100%)',
        opacity: visible ? 1 : 0,
        pointerEvents: visible ? ('auto' as const) : ('none' as const),
      }}
    >
      {/* 左侧：返回 */}
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={goBack}
        style={{
          borderColor: '#555B67',
          color: '#FCFBF8',
          borderRadius: 3,
          background: 'transparent',
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
          color: '#FCFBF8',
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
      <Space size={6} style={{ flexShrink: 0 }}>
        <Button
          icon={<CopyOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onCopy();
          }}
          size="small"
          style={{
            borderColor: '#555B67',
            color: '#FCFBF8',
            borderRadius: 3,
            background: 'transparent',
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
            background: '#2457FF',
            border: 'none',
            borderRadius: 3,
          }}
          title="下载 .md"
        />
        <Button
          icon={<VerticalAlignTopOutlined />}
          onClick={scrollToTop}
          size="small"
          style={{
            borderColor: '#555B67',
            color: atBottom ? '#B6E93D' : '#858B98',
            background: 'transparent',
            borderRadius: 3,
            transition: 'color 0.2s ease',
          }}
          title="回到顶部"
        />
      </Space>
    </div>
  );
}
