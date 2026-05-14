'use client'

import { useRef, useState } from 'react'
import { exportSession } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'

interface ExportButtonProps {
  sessionId: string
  disabled?: boolean
}

export function ExportButton({ sessionId, disabled = false }: ExportButtonProps) {
  const [exportingFormat, setExportingFormat] = useState<'csv' | 'json' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inFlightRef = useRef(false)

  async function handleExport(format: 'csv' | 'json') {
    if (inFlightRef.current) return
    inFlightRef.current = true
    setExportingFormat(format)
    setError(null)
    try {
      const token = await getAccessToken()
      await exportSession(sessionId, format, token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エクスポートに失敗しました')
    } finally {
      inFlightRef.current = false
      setExportingFormat(null)
    }
  }

  const isExporting = exportingFormat !== null

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <button
          onClick={() => handleExport('csv')}
          disabled={disabled || isExporting}
          className="
            flex-1 py-2 px-4 rounded text-xs font-semibold tracking-widest uppercase
            border border-[var(--border)] text-[var(--text-muted)]
            hover:border-[var(--accent)] hover:text-[var(--accent)]
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-all
          "
        >
          {exportingFormat === 'csv' ? '...' : 'CSV'}
        </button>
        <button
          onClick={() => handleExport('json')}
          disabled={disabled || isExporting}
          className="
            flex-1 py-2 px-4 rounded text-xs font-semibold tracking-widest uppercase
            border border-[var(--border)] text-[var(--text-muted)]
            hover:border-[var(--accent)] hover:text-[var(--accent)]
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-all
          "
        >
          {exportingFormat === 'json' ? '...' : 'JSON'}
        </button>
      </div>
      {error && <p className="text-xs text-[var(--danger)]">{error}</p>}
    </div>
  )
}
