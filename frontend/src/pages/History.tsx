import { useState } from 'react';
import { Select, Space, Input, Typography, Empty } from 'antd';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchHistory } from '../api/client';
import ArticleCard from '../components/ArticleCard';

const { Title } = Typography;

export default function History() {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['history', categoryFilter],
    queryFn: () => fetchHistory(categoryFilter),
  });

  const filtered = searchText
    ? articles.filter((a) => a.title.includes(searchText))
    : articles;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 20, fontWeight: 600 }}>
        历史记录
      </Title>

      <div style={{
        display: 'flex',
        gap: 12,
        marginBottom: 20,
        flexWrap: 'wrap',
      }}>
        <Select
          style={{ width: 160 }}
          placeholder="筛选分类"
          allowClear
          value={categoryFilter}
          onChange={(val) => setCategoryFilter(val)}
          options={[
            { value: 'tech', label: '🔧 技术趋势' },
            { value: 'finance', label: '💰 金融财经' },
            { value: 'business', label: '🏢 商业' },
            { value: 'entertainment', label: '🎬 娱乐文化' },
            { value: 'literature', label: '📚 文学艺术' },
            { value: 'world', label: '🌐 国际新闻' },
            { value: 'zhongyi', label: '🌿 中医中药' },
          ]}
        />
        <Input
          prefix={<SearchOutlined style={{ color: '#64748B' }} />}
          placeholder="搜索标题..."
          style={{ width: 260 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="glass"
              style={{
                height: 100,
                borderRadius: 12,
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <div style={{ width: '30%', height: 12, background: 'rgba(124, 58, 237, 0.08)', borderRadius: 4 }} />
              <div style={{ width: '60%', height: 14, background: 'rgba(124, 58, 237, 0.06)', borderRadius: 4 }} />
              <div style={{ width: '40%', height: 10, background: 'rgba(124, 58, 237, 0.04)', borderRadius: 4 }} />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '60px 0',
        }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span style={{ color: '#64748B' }}>
                {searchText ? '没有匹配的文章' : '暂无文章'}
              </span>
            }
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filtered.map((article) => (
            <ArticleCard key={`${article.category}-${article.slug}`} article={article} />
          ))}
        </div>
      )}
    </div>
  );
}
