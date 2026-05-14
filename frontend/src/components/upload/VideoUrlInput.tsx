'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { uploadYouTube } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'

const YOUTUBE_PATTERN = /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/

export function VideoUrlInput() {
  const router = useRouter()
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!YOUTUBE_PATTERN.test(url)) {
      setError('有効な YouTube URL を入力してください')
      return
    }

    setLoading(true)
    try {
      const token = await getAccessToken()
      const { session_id } = await uploadYouTube(url, token)
      router.push(`/analysis/${session_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'URL の送信に失敗しました')
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
            <svg
              className="w-4 h-4 text-[var(--text-muted)]"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.22 6.22 0 0 0-.79-.05A6.34 6.34 0 0 0 3.15 15.2a6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.22 8.22 0 0 0 4.82 1.55V6.79a4.85 4.85 0 0 1-1.05-.1z" />
            </svg>
          </div>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            disabled={loading}
            className="
              w-full pl-10 pr-4 py-3 rounded-lg text-sm
              bg-[var(--surface-2)] border border-[var(--border)]
              text-[var(--text)] placeholder-[var(--text-muted)]
              focus:outline-none focus:border-[var(--accent)]
              transition-colors disabled:opacity-50
            "
          />
        </div>
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="
            px-5 py-3 rounded-lg text-sm font-semibold tracking-widest uppercase
            bg-[var(--accent)] text-white
            hover:brightness-110 active:brightness-95
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-all
          "
        >
          {loading ? '送信中...' : '解析'}
        </button>
      </div>
      {error && (
        <p className="mt-2 text-sm text-[var(--danger)]">{error}</p>
      )}
    </form>
  )
}
