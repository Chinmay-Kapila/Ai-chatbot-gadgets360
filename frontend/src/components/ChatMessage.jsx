import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { AlertCircle, Database, Sparkles } from 'lucide-react'
import CodeBlock from './CodeBlock'
import ProductCard from './ProductCard'
import ArticleCard from './ArticleCard'
import RelatedLinks from './RelatedLinks'

/**
 * Renders a single message bubble: user messages are plain text on a
 * brand-colored bubble; assistant messages render full markdown plus any
 * product cards, article cards, related links, and a metadata footnote.
 */
function ChatMessage({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end animate-slideUp">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-500 px-4 py-2.5 text-sm text-white shadow-sm">
          {message.content}
        </div>
      </div>
    )
  }

  const hasProducts = message.product_cards && message.product_cards.length > 0
  const hasArticles = message.article_cards && message.article_cards.length > 0
  const hasLinks = message.related_links && message.related_links.length > 0
  const meta = message.metadata

  return (
    <div className="flex justify-start animate-slideUp">
      <div className="flex max-w-[92%] flex-col gap-2">
        <div
          className={`rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm ${
            message.isError
              ? 'border border-brand-200 bg-brand-50 dark:border-brand-800/50 dark:bg-brand-900/20'
              : message.rejected
              ? 'border border-ink-200 bg-ink-50 dark:border-ink-700 dark:bg-ink-800/60'
              : 'bg-ink-100 dark:bg-ink-800'
          }`}
        >
          {message.isError && (
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-400">
              <AlertCircle size={13} />
              Couldn&apos;t get a response
            </div>
          )}

          {message.format === 'markdown' ? (
            <div className="g360-markdown">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code: CodeBlock,
                  a: ({ children, ...props }) => (
                    <a {...props} target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-ink-800 dark:text-ink-100">
              {message.content}
            </p>
          )}
        </div>

        {hasProducts && (
          <div className="scrollbar-thin flex gap-3 overflow-x-auto pb-1">
            {message.product_cards.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}

        {hasArticles && (
          <div className="scrollbar-thin flex gap-3 overflow-x-auto pb-1">
            {message.article_cards.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}

        {hasLinks && <RelatedLinks links={message.related_links} />}

        {meta && (
          <div className="flex items-center gap-1.5 px-1 text-[0.65rem] text-ink-400 dark:text-ink-500">
            {meta.used_gemini ? (
              <Sparkles size={11} className="text-brand-400" />
            ) : (
              <Database size={11} />
            )}
            <span className="capitalize">{meta.intent?.replace('_', ' ')}</span>
            {meta.entity && meta.entity !== 'none' && (
              <>
                <span>·</span>
                <span className="capitalize">{meta.entity}</span>
              </>
            )}
            {meta.source_apis?.length > 0 && (
              <>
                <span>·</span>
                <span>{meta.source_apis.join(', ')}</span>
              </>
            )}
            {meta.cached && (
              <>
                <span>·</span>
                <span>cached</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
