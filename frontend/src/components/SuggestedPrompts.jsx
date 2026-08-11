import { Cpu, Newspaper, TrendingUp, Smartphone } from 'lucide-react'

const PROMPTS = [
  { icon: Smartphone, label: 'Best phones under ₹30,000', value: 'Suggest the best phones under ₹30,000 with a good camera' },
  { icon: Cpu, label: 'Compare two laptops', value: 'Compare Apple MacBook Air with Dell Inspiron' },
  { icon: Newspaper, label: "Today's tech news", value: "What's the latest tech news today?" },
]

/**
 * Quick-start suggestion chips shown above the input when the
 * conversation is fresh, so users know what the assistant can help with.
 */
function SuggestedPrompts({ onSelect, disabled }) {
  return (
    <div className="flex flex-wrap gap-1.5 px-4 pb-2">
      {PROMPTS.map(({ icon: Icon, label, value }) => (
        <button
          key={label}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(value)}
          className="flex items-center gap-1.5 rounded-full border border-ink-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-600 transition-colors hover:border-brand-300 hover:text-brand-600 disabled:cursor-not-allowed disabled:opacity-50 dark:border-ink-700 dark:bg-ink-800 dark:text-ink-300 dark:hover:text-brand-400"
        >
          <Icon size={13} className="text-brand-500" />
          {label}
        </button>
      ))}
    </div>
  )
}

export default SuggestedPrompts