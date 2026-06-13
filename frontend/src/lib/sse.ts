import type { SSEDamageEvent, SSEDoneEvent, SSEErrorEvent } from '@/types'

export interface SSEHandlers {
  onDamage: (event: SSEDamageEvent) => void
  onDone: (event: SSEDoneEvent) => void
  onError: (event: SSEErrorEvent) => void
  onConnectionError?: () => void
}

function safeParse<T>(data: string, onFailure: () => void): T | null {
  try {
    return JSON.parse(data) as T
  } catch {
    onFailure()
    return null
  }
}

export function connectSSE(url: string, handlers: SSEHandlers): () => void {
  const es = new EventSource(url)

  es.addEventListener('damage', (e: MessageEvent) => {
    // Parse failure on a single frame is non-fatal — skip and continue streaming
    const data = safeParse<SSEDamageEvent>(e.data, () => {})
    if (data) handlers.onDamage(data)
  })

  es.addEventListener('done', (e: MessageEvent) => {
    const data = safeParse<SSEDoneEvent>(e.data, () => handlers.onConnectionError?.())
    if (data) handlers.onDone(data)
    es.close()
  })

  es.addEventListener('error', (e: Event) => {
    if (e instanceof MessageEvent) {
      const data = safeParse<SSEErrorEvent>(e.data, () => handlers.onConnectionError?.())
      if (data) handlers.onError(data)
      es.close()
    }
    // Connection-level errors are handled exclusively by onerror below
  })

  es.onerror = () => {
    handlers.onConnectionError?.()
    es.close()
  }

  return () => es.close()
}
