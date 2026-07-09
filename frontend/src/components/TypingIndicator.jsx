/**
 * Three-dot "assistant is typing" indicator, shown inside a message
 * bubble while waiting for the backend response.
 */
function TypingIndicator() {
  return (
    <div
      className="flex w-fit items-center gap-1.5 rounded-2xl rounded-bl-sm bg-ink-100 px-4 py-3 dark:bg-ink-800"
      role="status"
      aria-label="Assistant is typing"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-ink-400 dark:bg-ink-400 animate-typingDot"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}

export default TypingIndicator
