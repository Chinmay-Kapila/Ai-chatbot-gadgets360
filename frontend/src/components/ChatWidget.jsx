import { useState } from 'react'
import { MessageCircle, X } from 'lucide-react'
import ChatWindow from './ChatWindow'
import useChat from '../hooks/useChat'
import useTheme from '../hooks/useTheme'

/**
 * Root floating chatbot widget. Mounts a launcher button fixed to the
 * bottom-right corner of the viewport; clicking it reveals the chat
 * panel. Owns the chat and theme hooks and passes state/handlers down.
 */
function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const { messages, sendMessage, isSending, error, dismissError, retryLast } = useChat()
  const { isDark, toggleTheme } = useTheme()

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3">
      {isOpen && (
        <ChatWindow
          messages={messages}
          isSending={isSending}
          error={error}
          onSend={sendMessage}
          onRetry={retryLast}
          onDismissError={dismissError}
          onClose={() => setIsOpen(false)}
          isDark={isDark}
          onToggleTheme={toggleTheme}
        />
      )}

      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? 'Close Gadgets360 AI Assistant' : 'Open Gadgets360 AI Assistant'}
        aria-expanded={isOpen}
        className="relative flex h-14 w-14 items-center justify-center rounded-full bg-brand-500 text-white shadow-launcher transition-transform hover:scale-105 active:scale-95"
      >
        {!isOpen && (
          <span className="absolute inset-0 rounded-full bg-brand-500 animate-pulseRing" />
        )}
        <span className="relative">
          {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
        </span>
      </button>
    </div>
  )
}

export default ChatWidget
