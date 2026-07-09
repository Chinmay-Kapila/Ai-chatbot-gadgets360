import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 20000
const MAX_RETRIES = Number(import.meta.env.VITE_API_MAX_RETRIES) || 2

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Determine whether a failed request is safe/sensible to retry.
 * Network errors, timeouts, and 5xx server errors are retried.
 * 4xx client errors are not, since retrying won't change the outcome.
 */
function isRetryable(error) {
  if (error.code === 'ECONNABORTED') return true
  if (!error.response) return true
  return error.response.status >= 500
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Wrap an axios call with retry + exponential backoff, and normalize
 * errors into a consistent, human-readable shape so UI components never
 * have to deal with raw axios/network error objects.
 */
async function withRetry(requestFn, { retries = MAX_RETRIES } = {}) {
  let attempt = 0
  let lastError = null

  while (attempt <= retries) {
    try {
      const response = await requestFn()
      return response.data
    } catch (error) {
      lastError = error

      if (attempt < retries && isRetryable(error)) {
        const backoffMs = 400 * Math.pow(2, attempt)
        await sleep(backoffMs)
        attempt += 1
        continue
      }

      throw normalizeError(error)
    }
  }

  throw normalizeError(lastError)
}

function normalizeError(error) {
  if (!error) {
    return { message: 'Something went wrong. Please try again.', status: null }
  }

  if (error.code === 'ECONNABORTED') {
    return {
      message: 'The assistant took too long to respond. Please try again.',
      status: null,
      code: 'TIMEOUT',
    }
  }

  if (!error.response) {
    return {
      message: "Can't reach the assistant right now. Check your connection and try again.",
      status: null,
      code: 'NETWORK_ERROR',
    }
  }

  const status = error.response.status
  const detail = error.response.data?.detail

  if (status === 502) {
    return {
      message: detail || 'The assistant is temporarily unavailable. Please try again shortly.',
      status,
      code: 'UPSTREAM_ERROR',
    }
  }

  if (status >= 500) {
    return {
      message: detail || 'Something went wrong on our end. Please try again.',
      status,
      code: 'SERVER_ERROR',
    }
  }

  if (status === 422) {
    return {
      message: 'That message could not be processed. Try rephrasing it.',
      status,
      code: 'VALIDATION_ERROR',
    }
  }

  return {
    message: detail || 'Something went wrong. Please try again.',
    status,
    code: 'REQUEST_ERROR',
  }
}

/**
 * Send a chat message to the assistant.
 * @param {string} message
 * @param {string|null} sessionId
 */
export async function sendMessage(message, sessionId) {
  return withRetry(() =>
    client.post('/chat', {
      message,
      session_id: sessionId || null,
    })
  )
}

/**
 * Check backend liveness/readiness.
 */
export async function healthCheck() {
  return withRetry(() => client.get('/health'), { retries: 1 })
}

export default {
  sendMessage,
  healthCheck,
}
