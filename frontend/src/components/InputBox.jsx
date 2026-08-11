import { useRef, useState } from 'react'
import { Send } from 'lucide-react'

const MAX_LENGTH = 2000

/**
 * Auto-growing textarea input with a send button. Enter sends the
 * message; Shift+Enter inserts a newline.
 */
function InputBox({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const handleChange = (event) => {
    setValue(event.target.value.slice(0, MAX_LENGTH))
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 96)}px`
    }
  }

  const submit = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex items-end gap-2 px-4 py-3">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Ask about phones, laptops, tech news…"
        aria-label="Message the Gadgets360 AI Assistant"
        className="max-h-24 flex-1 resize-none rounded-xl border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 disabled:opacity-60 dark:border-ink-700 dark:bg-ink-800 dark:text-ink-100"
      />
      <button
        type="button"
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-500 text-white transition-colors hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-ink-300 dark:disabled:bg-ink-700"
      >
        <Send size={17} />
      </button>
    </div>
  )
}

export default InputBox
