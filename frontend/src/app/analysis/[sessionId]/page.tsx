'use client'

import { use } from 'react'
import { useAnalysisStream } from '@/hooks/useAnalysisStream'
import { DamageLogViewer } from '@/components/analysis/DamageLogViewer'
import { SummaryCard } from '@/components/analysis/SummaryCard'
import { ExportButton } from '@/components/analysis/ExportButton'
import { ProgressBar } from '@/components/common/ProgressBar'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

interface AnalysisPageProps {
  params: Promise<{ sessionId: string }>
}

export default function AnalysisPage({ params }: AnalysisPageProps) {
  const { sessionId } = use(params)
  const { entries, progress, summary, status, error } = useAnalysisStream(sessionId)

  const isDone = status === 'done'
  const isError = status === 'error'
  const isConnecting = status === 'connecting'

  const statusLabel = {
    connecting: '接続中',
    streaming: '解析中',
    done: '完了',
    error: 'エラー',
  }[status]

  const statusColor = {
    connecting: 'text-[var(--text-muted)]',
    streaming: 'text-[var(--accent)]',
    done: 'text-[var(--success)]',
    error: 'text-[var(--danger)]',
  }[status]

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="border-b border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <div className="mx-auto max-w-7xl flex items-center gap-6">
          <div className="flex items-center gap-2 shrink-0">
            {isConnecting && <LoadingSpinner size="sm" />}
            {status === 'streaming' && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--accent)] opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--accent)]" />
              </span>
            )}
            <span className={`text-xs font-semibold tracking-widest uppercase ${statusColor}`}>
              {statusLabel}
            </span>
          </div>
          <div className="flex-1">
            {(status === 'streaming' || isDone) && (
              <ProgressBar value={progress} showPercent={!isDone} />
            )}
          </div>
          <span className="shrink-0 text-xs text-[var(--text-muted)] font-mono">
            {entries.length} hits
          </span>
        </div>
      </div>

      {isError && (
        <div className="mx-auto max-w-7xl w-full px-4 pt-6">
          <div className="rounded-lg border border-[var(--danger)]/40 bg-[var(--danger)]/10 p-4 text-sm text-[var(--danger)]">
            {error ?? '解析中にエラーが発生しました'}
          </div>
        </div>
      )}

      <div className="flex-1 flex min-h-0 mx-auto w-full max-w-7xl divide-x divide-[var(--border)]">
        <div className="flex-1 flex flex-col min-h-0 min-w-0">
          <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)]">
            <span className="text-xs tracking-widest uppercase text-[var(--text-muted)]">
              ダメージログ
            </span>
          </div>
          <DamageLogViewer entries={entries} streaming={status === 'streaming'} />
        </div>

        <div className="w-72 shrink-0 flex flex-col gap-4 p-4">
          <span className="text-xs tracking-widest uppercase text-[var(--text-muted)]">
            サマリー
          </span>
          <SummaryCard summary={summary} entryCount={entries.length} streaming={status === 'streaming'} />
          {isDone && (
            <div className="mt-auto">
              <p className="text-xs tracking-widest uppercase text-[var(--text-muted)] mb-2">
                エクスポート
              </p>
              <ExportButton sessionId={sessionId} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
