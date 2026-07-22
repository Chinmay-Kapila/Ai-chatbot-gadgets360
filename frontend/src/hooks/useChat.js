import { useCallback, useRef, useState } from 'react'
import { sendMessage as sendMessageRequest } from '../services/api'

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

const WELCOME_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Hi! I'm the Gadgets360 AI Assistant. Ask me about phones, laptops, tablets, smartwatches, TVs, tech news, reviews, comparisons, buying guides, or finance topics like crypto, gold, silver, fuel, and stock prices.",
  format: 'markdown',
  product_cards: [],
  article_cards: [],
  related_links: [],
  metadata: null,
  rejected: false,
  isError: false,
}

/**
 * Manages the full chat conversation: message history, backend session_id,
 * loading/typing state, and error handling. No persistent storage is used
 * — everything lives in component state and resets on reload.
 */
export function useChat() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState(null)
  const sessionIdRef = useRef(null)
  const lastFailedMessageRef = useRef(null)

  const pushMessage = useCallback((message) => {
    setMessages((prev) => [...prev, message])
  }, [])

  /**
   * Performs the actual API call and appends the resulting assistant
   * message (success or error). Does NOT touch the user-message side of
   * the conversation — callers (send / retryLast) own that, so a retry
   * never duplicates the original user bubble.
   */
  const performRequest = useCallback(
    async (trimmed) => {
      setIsSending(true)

      try {
        const data = await sendMessageRequest(trimmed, sessionIdRef.current)
        sessionIdRef.current = data.session_id || sessionIdRef.current
        lastFailedMessageRef.current = null

        pushMessage({
          id: makeId(),
          role: 'assistant',
          content: data.answer,
          format: data.format || 'markdown',
          product_cards: data.product_cards || [],
          article_cards: data.article_cards || [],
          related_links: data.related_links || [],
          metadata: data.metadata || null,
          rejected: Boolean(data.rejected),
          isError: false,
        })
      } catch (err) {
        lastFailedMessageRef.current = trimmed
        setError(err.message || 'Something went wrong. Please try again.')

        pushMessage({
          id: makeId(),
          role: 'assistant',
          content:
            err.message || "I couldn't process that. Please try again in a moment.",
          format: 'text',
          product_cards: [],
          article_cards: [],
          related_links: [],
          metadata: null,
          rejected: false,
          isError: true,
        })
      } finally {
        setIsSending(false)
      }
    },
    [pushMessage]
  )

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed || isSending) return

      setError(null)

      pushMessage({
        id: makeId(),
        role: 'user',
        content: trimmed,
        format: 'text',
        product_cards: [],
        article_cards: [],
        related_links: [],
        metadata: null,
        rejected: false,
        isError: false,
      })

      await performRequest(trimmed)
    },
    [isSending, pushMessage, performRequest]
  )

  const retryLast = useCallback(() => {
    const lastFailed = lastFailedMessageRef.current
    if (!lastFailed || isSending) return

    setError(null)
    // Remove only the failed assistant bubble — the original user
    // message stays exactly as it was, so retrying never duplicates it.
    setMessages((prev) => prev.filter((m) => !m.isError))
    performRequest(lastFailed)
  }, [isSending, performRequest])

  const dismissError = useCallback(() => setError(null), [])

  return {
    messages,
    sendMessage: send,
    isSending,
    error,
    dismissError,
    retryLast,
    sessionId: sessionIdRef.current,
  }
}

export default useChat
