'use client'

import { useEffect, useRef, useState } from 'react'
import { connectSSE } from '@/lib/sse'
import type { AnalysisStatus, DamageSummary, SSEDamageEvent } from '@/types'

export interface StreamDamageEntry {
  id: string
  timestamp_ms: number
  damage_value: number
}

export interface AnalysisStreamState {
  entries: StreamDamageEntry[]
  progress: number
  summary: DamageSummary | null
  status: AnalysisStatus
  error: string | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''
const MISSING_API_BASE = !API_BASE

export function useAnalysisStream(sessionId: string): AnalysisStreamState {
  const [entries, setEntries] = useState<StreamDamageEntry[]>([])
  const [progress, setProgress] = useState(0)
  const [summary, setSummary] = useState<DamageSummary | null>(null)
  // Derive initial status/error at render time so we don't setState inside the effect
  const [status, setStatus] = useState<AnalysisStatus>(
    MISSING_API_BASE ? 'error' : 'connecting'
  )
  const [error, setError] = useState<string | null>(
    MISSING_API_BASE ? 'NEXT_PUBLIC_API_BASE_URL が設定されていません' : null
  )
  const idRef = useRef(0)

  useEffect(() => {
    if (MISSING_API_BASE) return

    const url = `${API_BASE}/api/v1/analysis/${sessionId}/stream`

    const disconnect = connectSSE(url, {
      onDamage: (event: SSEDamageEvent) => {
        setStatus('streaming')
        setProgress(event.progress)
        setEntries((prev) => [
          ...prev,
          {
            id: String(idRef.current++),
            timestamp_ms: event.timestamp_ms,
            damage_value: event.damage_value,
          },
        ])
      },
      onDone: (event) => {
        setSummary(event)
        setProgress(100)
        setStatus('done')
      },
      onError: (event) => {
        setError(event.message)
        setStatus('error')
      },
      onConnectionError: () => {
        setError('サーバーとの接続が切断されました')
        setStatus('error')
      },
    })

    return disconnect
  }, [sessionId])

  return { entries, progress, summary, status, error }
}
