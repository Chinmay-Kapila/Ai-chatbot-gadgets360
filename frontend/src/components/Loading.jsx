import { Loader2 } from 'lucide-react'

/**
 * Generic inline loading spinner with optional label.
 * Used for initial health checks or any blocking async state.
 */
function Loading({ label = 'Loading', size = 16, className = '' }) {
  return (
    <div className={`flex items-center gap-2 text-ink-400 dark:text-ink-400 ${className}`}>
      <Loader2 size={size} className="animate-spin text-brand-500" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  )
}

export default Loading
