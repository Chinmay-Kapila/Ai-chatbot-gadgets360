import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

/**
 * Custom renderer for fenced code blocks inside markdown answers.
 * Adds a copy-to-clipboard affordance and monospace styling.
 */
function CodeBlock({ inline, className, children }) {
  const [copied, setCopied] = useState(false)
  const codeText = String(children).replace(/\n$/, '')
  const language = /language-(\w+)/.exec(className || '')?.[1]

  if (inline) {
    return (
      <code className="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[0.85em] text-brand-600 dark:bg-ink-800 dark:text-brand-400">
        {children}
      </code>
    )
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(codeText)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-ink-200 dark:border-ink-700">
      <div className="flex items-center justify-between bg-ink-100 px-3 py-1.5 dark:bg-ink-800">
        <span className="font-mono text-xs text-ink-500 dark:text-ink-400">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-ink-500 transition-colors hover:text-brand-500 dark:text-ink-400"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="scrollbar-thin overflow-x-auto bg-ink-950 p-3 text-ink-100">
        <code className="font-mono text-[0.82rem] leading-relaxed">{codeText}</code>
      </pre>
    </div>
  )
}

export default CodeBlock
