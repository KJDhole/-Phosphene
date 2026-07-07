import { Checkbox, Spin } from 'antd';
import { ApiOutlined, SyncOutlined, LinkOutlined, RightOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchCategories, type Category } from '../api/client';

interface Props {
  selected: string[];
  onChange: (selected: string[]) => void;
}

const typeMeta: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  api: { icon: <ApiOutlined />, color: '#7C3AED', label: 'API' },
  rss: { icon: <SyncOutlined />, color: '#10B981', label: 'RSS' },
  scrapling: { icon: <LinkOutlined />, color: '#F59E0B', label: '爬虫' },
};

export default function CategoryPicker({ selected, onChange }: Props) {
  const { data: categories, isLoading } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  });

  if (isLoading) return <Spin />;

  return (
    <div className="category-grid">
      {categories?.map((cat) => {
        const isChecked = selected.includes(cat.name);

        /* Deduplicate source types */
        const typeCounts: Record<string, number> = {};
        cat.sources.forEach((s) => {
          typeCounts[s.type] = (typeCounts[s.type] || 0) + 1;
        });
        const uniqueTypes = Object.keys(typeCounts);

        return (
          <div
            key={cat.name}
            className={`category-card ${isChecked ? 'selected' : ''}`}
            onClick={() => {
              if (isChecked) {
                onChange(selected.filter((n) => n !== cat.name));
              } else {
                onChange([...selected, cat.name]);
              }
            }}
            role="checkbox"
            aria-checked={isChecked}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (isChecked) {
                  onChange(selected.filter((n) => n !== cat.name));
                } else {
                  onChange([...selected, cat.name]);
                }
              }
            }}
          >
            {/* Selection indicator */}
            <div className="category-check">
              <Checkbox checked={isChecked} />
            </div>

            {/* Emoji + Name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="category-emoji">{cat.emoji}</span>
              <span className="category-name">{cat.display_name}</span>
            </div>

            {/* Source count */}
            <div className="category-meta">
              <span>{cat.sources.length}</span> 个数据源
            </div>

            {/* Source type badges */}
            {uniqueTypes.length > 0 && (
              <div className="category-types">
                {uniqueTypes.map((type) => {
                  const meta = typeMeta[type];
                  if (!meta) return null;
                  return (
                    <span
                      key={type}
                      className="type-badge"
                      style={{
                        background: `${meta.color}0d`,
                        color: meta.color,
                        borderColor: `${meta.color}25`,
                      }}
                    >
                      <span className="type-dot" style={{ background: meta.color }} />
                      <span>{meta.label}</span>
                      {typeCounts[type] > 1 && (
                        <span className="type-count">×{typeCounts[type]}</span>
                      )}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
