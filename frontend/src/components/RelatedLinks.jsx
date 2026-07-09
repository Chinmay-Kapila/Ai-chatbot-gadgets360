import { Link2 } from 'lucide-react'

/**
 * Renders the related_links array as a compact list of clickable chips
 * that open in a new tab.
 */
function RelatedLinks({ links }) {
  if (!links || links.length === 0) return null

  return (
    <div className="mt-2 flex flex-col gap-1.5">
      <span className="text-[0.68rem] font-semibold uppercase tracking-wide text-ink-400 dark:text-ink-500">
        Related links
      </span>
      <div className="flex flex-wrap gap-1.5">
        {links.map((link, index) => (
          <a
            key={`${link.url}-${index}`}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-full border border-ink-200 bg-ink-50 px-2.5 py-1 text-[0.72rem] text-ink-600 transition-colors hover:border-brand-300 hover:text-brand-600 dark:border-ink-700 dark:bg-ink-800 dark:text-ink-300 dark:hover:text-brand-400"
          >
            <Link2 size={11} />
            <span className="max-w-[10rem] truncate">{link.title}</span>
          </a>
        ))}
      </div>
    </div>
  )
}

export default RelatedLinks
