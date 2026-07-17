import { useMemo, useState } from 'react';
import { Alert, Empty, Input, Select, Skeleton } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchCategories, fetchHistory } from '../api/client';
import ArticleCard from '../components/ArticleCard';
import { useHistory } from '../stores/HistoryContext';

export default function History() {
  const { categoryFilter, setCategoryFilter, searchText, setSearchText } = useHistory();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: fetchCategories });
  const { data: articles = [], isLoading, isError } = useQuery({
    queryKey: ['history', categoryFilter],
    queryFn: () => fetchHistory(categoryFilter),
  });

  const filtered = useMemo(() => articles.filter((article) => {
    const titleMatches = !searchText || article.title.toLowerCase().includes(searchText.toLowerCase());
    const statusMatches = !statusFilter || article.review_status === statusFilter;
    return titleMatches && statusMatches;
  }), [articles, searchText, statusFilter]);

  return (
    <div className="archive-page">
      <section className="page-heading editorial-heading archive-heading">
        <div>
          <span className="section-eyebrow">CONTENT ARCHIVE / {articles.length} ISSUES</span>
          <h1>内容档案</h1>
          <p>每一篇内容都保留来源、校验和审核轨迹。</p>
        </div>
      </section>

      <div className="archive-toolbar">
        <div className="archive-search">
          <SearchOutlined />
          <Input
            variant="borderless"
            placeholder="搜索文章标题"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            allowClear
          />
        </div>
        <Select
          value={categoryFilter}
          onChange={setCategoryFilter}
          allowClear
          placeholder="全部分类"
          options={categories.map((category) => ({ value: category.name, label: `${category.emoji} ${category.display_name}` }))}
        />
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          allowClear
          placeholder="全部状态"
          options={[
            { value: 'awaiting_review', label: '待审核' },
            { value: 'changes_requested', label: '需修改' },
            { value: 'approved', label: '已通过' },
            { value: 'legacy_unverified', label: '旧版未验证' },
          ]}
        />
        <span className="archive-result-count">{filtered.length} RESULTS</span>
      </div>

      {isError ? (
        <Alert type="error" showIcon message="无法加载内容档案" description="请检查后端服务和输出目录。" />
      ) : isLoading ? (
        <div className="loading-sheet"><Skeleton active paragraph={{ rows: 9 }} /></div>
      ) : filtered.length === 0 ? (
        <div className="editorial-empty"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有符合条件的内容" /></div>
      ) : (
        <section className="archive-list">
          {filtered.map((article) => <ArticleCard key={`${article.category}-${article.slug}`} article={article} />)}
        </section>
      )}
    </div>
  );
}
