import { Alert, Spin } from 'antd';
import { CheckOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchCategories, type Category } from '../api/client';

interface Props {
  selected: string[];
  onChange: (selected: string[]) => void;
}

const typeLabels: Record<string, string> = {
  api: 'API',
  rss: 'RSS',
  scrapling: 'WEB',
};

export default function CategoryPicker({ selected, onChange }: Props) {
  const { data: categories = [], isLoading, isError } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  });

  if (isLoading) return <div className="picker-loading"><Spin /> 读取信源配置…</div>;
  if (isError) return <Alert type="error" message="无法读取分类，请检查后端服务" />;

  const toggle = (name: string) => {
    onChange(
      selected.includes(name)
        ? selected.filter((value) => value !== name)
        : [...selected, name],
    );
  };

  return (
    <div className="category-grid">
      {categories.map((category, index) => {
        const checked = selected.includes(category.name);
        const sourceTypes = Array.from(new Set(category.sources.map((source) => source.type)));
        return (
          <button
            type="button"
            key={category.name}
            className={`category-card ${checked ? 'selected' : ''}`}
            onClick={() => toggle(category.name)}
            aria-pressed={checked}
          >
            <span className="category-order">0{index + 1}</span>
            <span className="category-select-indicator">
              {checked ? <CheckOutlined /> : <i />}
            </span>
            <span className="category-emoji">{category.emoji}</span>
            <span className="category-name">{category.display_name}</span>
            <span className="category-description">{category.description}</span>
            <span className="category-footer">
              <b>{category.sources.length}</b> 个信源
              <span className="category-types">
                {sourceTypes.map((type) => (
                  <i key={type}>{typeLabels[type] || type.toUpperCase()}</i>
                ))}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
