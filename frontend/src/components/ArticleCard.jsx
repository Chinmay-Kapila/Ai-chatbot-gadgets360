import { ExternalLink, Newspaper } from 'lucide-react'
import { useState } from 'react'

/**
 * Renders a single article/review/news card: thumbnail, title, summary,
 * and a link out to the full article on Gadgets360.
 */
function ArticleCard({ article }) {
  const [imgError, setImgError] = useState(false)

  return (
    <a
      href={article.url || undefined}
      target={article.url ? '_blank' : undefined}
      rel={article.url ? 'noopener noreferrer' : undefined}
      className="flex w-64 shrink-0 gap-3 overflow-hidden rounded-xl2 border border-ink-200 bg-white p-3 shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md dark:border-ink-700 dark:bg-ink-800"
    >
      <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-ink-100 dark:bg-ink-900">
        {article.image_url && !imgError ? (
          <img
            src={article.image_url}
            alt={article.title}
            onError={() => setImgError(true)}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <Newspaper size={18} className="text-ink-300 dark:text-ink-600" />
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {article.category && (
          <span className="font-mono text-[0.62rem] uppercase tracking-wide text-brand-500">
            {article.category}
          </span>
        )}
        <h4 className="line-clamp-2 font-display text-sm font-semibold leading-snug text-ink-900 dark:text-white">
          {article.title}
        </h4>
        {article.summary && (
          <p className="line-clamp-2 text-[0.72rem] text-ink-500 dark:text-ink-400">
            {article.summary}
          </p>
        )}
        {article.url && (
          <span className="mt-auto flex items-center gap-1 text-[0.72rem] font-medium text-brand-500">
            Read article
            <ExternalLink size={11} />
          </span>
        )}
      </div>
    </a>
  )
}

export default ArticleCard
