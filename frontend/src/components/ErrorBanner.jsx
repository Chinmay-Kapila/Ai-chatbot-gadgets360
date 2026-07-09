import { AlertTriangle, RotateCcw, X } from 'lucide-react'

/**
 * Inline error banner shown above the input when the last request
 * failed. Offers a retry action and a dismiss control.
 */
function ErrorBanner({ message, onRetry, onDismiss }) {
  if (!message) return null

  return (
    <div className="mx-4 mb-2 flex items-start gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-xs text-brand-700 dark:border-brand-800/50 dark:bg-brand-900/20 dark:text-brand-300">
      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
      <p className="flex-1">{message}</p>
      <div className="flex shrink-0 items-center gap-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1 font-semibold hover:underline"
          >
            <RotateCcw size={12} />
            Retry
          </button>
        )}
        <button type="button" onClick={onDismiss} aria-label="Dismiss error">
          <X size={13} />
        </button>
      </div>
    </div>
  )
}

export default ErrorBanner
