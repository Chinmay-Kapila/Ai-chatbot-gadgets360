import { useEffect, useRef } from 'react'
import Header from './Header'
import Footer from './Footer'
import ChatMessage from './ChatMessage'
import TypingIndicator from './TypingIndicator'
import SuggestedPrompts from './SuggestedPrompts'
import ErrorBanner from './ErrorBanner'
import InputBox from './InputBox'

/**
 * The full chat panel: header, scrollable message history (with
 * auto-scroll on new messages), typing indicator, suggested prompts for
 * a fresh conversation, error banner, input box, and footer.
 */
function ChatWindow({
  messages,
  isSending,
  error,
  onSend,
  onRetry,
  onDismissError,
  onClose,
  isDark,
  onToggleTheme,
}) {
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }
  }, [messages, isSending])

  const showSuggestions = messages.length <= 1 && !isSending

  return (
    <div className="flex h-[34rem] w-[23rem] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-xl2 border border-ink-200 bg-white shadow-panel dark:border-ink-700 dark:bg-ink-900 sm:h-[36rem] sm:w-96">
      <Header onClose={onClose} isDark={isDark} onToggleTheme={onToggleTheme} />

      <div
        ref={scrollRef}
        className="scrollbar-thin flex-1 space-y-4 overflow-y-auto bg-ink-50 px-4 py-4 dark:bg-ink-950"
      >
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isSending && <TypingIndicator />}
      </div>

      {showSuggestions && (
        <SuggestedPrompts onSelect={onSend} disabled={isSending} />
      )}

      <ErrorBanner message={error} onRetry={onRetry} onDismiss={onDismissError} />

      <div className="border-t border-ink-100 dark:border-ink-800">
        <InputBox onSend={onSend} disabled={isSending} />
      </div>

      <Footer />
    </div>
  )
}

export default ChatWindow
