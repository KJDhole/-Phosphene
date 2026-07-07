import { Tabs } from 'antd';
import { FileTextOutlined, TwitterOutlined, MailOutlined, VideoCameraOutlined, GlobalOutlined } from '@ant-design/icons';
import MarkdownRenderer from './MarkdownRenderer';

interface Props {
  formats: Record<string, string>;
  activeKey: string;
  onChange: (key: string) => void;
}

const formatMeta: Record<string, { label: string; icon: React.ReactNode }> = {
  blog: { label: '博客', icon: <FileTextOutlined /> },
  twitter: { label: '推文', icon: <TwitterOutlined /> },
  newsletter: { label: '通讯', icon: <MailOutlined /> },
  video_script: { label: '脚本', icon: <VideoCameraOutlined /> },
  english: { label: 'English', icon: <GlobalOutlined /> },
};

export default function FormatTabs({ formats, activeKey, onChange }: Props) {
  const items = Object.entries(formats).map(([key, content]) => ({
    key,
    label: (
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {formatMeta[key]?.icon}
        <span>{formatMeta[key]?.label || key}</span>
      </span>
    ),
    children: (
      <div className="glass" style={{ padding: 24, borderRadius: 12, marginTop: 4 }}>
        <MarkdownRenderer content={content} />
      </div>
    ),
  }));

  return (
    <Tabs
      activeKey={activeKey}
      onChange={onChange}
      items={items}
      style={{ borderRadius: 12 }}
    />
  );
}
