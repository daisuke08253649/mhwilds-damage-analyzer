'use client'

import React from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getHistory } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import type { AnalysisSession } from '@/types'

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

const statusLabel: Record<AnalysisSession['status'], string> = {
  pending: '待機中',
  processing: '処理中',
  done: '完了',
  error: 'エラー',
}

const statusColor: Record<AnalysisSession['status'], string> = {
  pending: 'text-[var(--text-muted)]',
  processing: 'text-[var(--accent)]',
  done: 'text-[var(--success)]',
  error: 'text-[var(--danger)]',
}

export default function HistoryPage(): React.JSX.Element {
  const { user } = useAuth()

  const {
    data: sessions = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['history', user?.id],
    queryFn: async () => {
      const token = await getAccessToken()
      if (!token) throw new Error('認証が必要です')
      return getHistory(token)
    },
    enabled: !!user,
  })

  return (
    <div className="flex-1 mx-auto w-full max-w-4xl px-4 py-8">
      <h1
        className="text-2xl font-black tracking-[0.12em] uppercase text-[var(--accent)] mb-8"
        style={{ fontFamily: 'var(--font-orbitron)' }}
      >
        HISTORY
      </h1>

      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="読み込み中" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-[var(--danger)]/40 bg-[var(--danger)]/10 p-4 text-sm text-[var(--danger)]">
          {error instanceof Error ? error.message : '履歴の取得に失敗しました'}
        </div>
      )}

      {!isLoading && !error && sessions.length === 0 && (
        <div className="text-center py-16">
          <p className="text-[var(--text-muted)] text-sm tracking-wide">
            解析履歴がありません
          </p>
          <Link
            href="/"
            className="mt-4 inline-block text-xs tracking-widest uppercase text-[var(--accent)] hover:underline"
          >
            動画を解析する →
          </Link>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="rounded-lg border border-[var(--border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--surface-2)]">
                <th className="px-4 py-3 text-left text-xs tracking-widest uppercase text-[var(--text-muted)] font-medium">
                  日時
                </th>
                <th className="px-4 py-3 text-left text-xs tracking-widest uppercase text-[var(--text-muted)] font-medium">
                  動画
                </th>
                <th className="px-4 py-3 text-right text-xs tracking-widest uppercase text-[var(--text-muted)] font-medium">
                  総ダメージ
                </th>
                <th className="px-4 py-3 text-center text-xs tracking-widest uppercase text-[var(--text-muted)] font-medium">
                  ステータス
                </th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session, i) => (
                <tr
                  key={session.id}
                  className={`border-b border-[var(--border)] hover:bg-[var(--surface-2)] transition-colors ${
                    i === sessions.length - 1 ? 'border-b-0' : ''
                  }`}
                >
                  <td className="px-4 py-3 text-xs text-[var(--text-muted)] whitespace-nowrap">
                    {formatDate(session.created_at)}
                  </td>
                  <td className="px-4 py-3 max-w-[200px] truncate text-[var(--text)]">
                    {session.status === 'done' || session.status === 'error' ? (
                      <Link
                        href={`/analysis/${session.id}`}
                        className="hover:text-[var(--accent)] transition-colors"
                      >
                        {session.video_name}
                      </Link>
                    ) : (
                      <span>{session.video_name}</span>
                    )}
                  </td>
                  <td
                    className="px-4 py-3 text-right tabular-nums text-[var(--accent)]"
                    style={{ fontFamily: 'var(--font-share-tech-mono)' }}
                  >
                    {session.total_damage != null
                      ? session.total_damage.toLocaleString()
                      : '---'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`text-xs font-medium tracking-wide ${statusColor[session.status]}`}
                    >
                      {statusLabel[session.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
