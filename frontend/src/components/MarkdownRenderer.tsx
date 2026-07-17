import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
  knownCitationIds?: Set<string>;
  onCitationClick?: (sourceId: string) => void;
}

function citationAnchor(sourceId: string) {
  return `#evidence-${sourceId.replace(':', '--')}`;
}

export default function MarkdownRenderer({ content, knownCitationIds, onCitationClick }: Props) {
  const canonicalContent = content.replace(
    /\[(?:证据(?:编号)?\s*[:：]?\s*)?([\w-]+)\s*[:：]\s*(\d+)\]/g,
    '[$1:$2]',
  );
  const linkedContent = canonicalContent.replace(
    /\[([\w-]+:\d+)\]/g,
    (_match, sourceId: string) => `[${sourceId}](${citationAnchor(sourceId)})`,
  );

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith('#evidence-')) {
              const sourceId = href.slice('#evidence-'.length).replace(/--(\d+)$/, ':$1');
              const missing = knownCitationIds ? !knownCitationIds.has(sourceId) : false;
              return (
                <button
                  type="button"
                  className={`citation-reference ${missing ? 'missing' : ''}`}
                  onClick={() => onCitationClick?.(sourceId)}
                  title={missing ? '该证据编号不存在' : '定位到引用证据'}
                >
                  {children}
                </button>
              );
            }
            return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
          },
        }}
      >
        {linkedContent}
      </ReactMarkdown>
    </div>
  );
}
