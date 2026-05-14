'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from '@/lib/auth'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const next = searchParams.get('next') ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const result = await signIn(email, password)
    setLoading(false)

    if ('error' in result) {
      setError(result.error)
      return
    }

    router.push(next)
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className="block text-xs tracking-widest uppercase text-[var(--text-muted)] mb-1.5">
          メールアドレス
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={loading}
          className="
            w-full px-4 py-3 rounded-lg text-sm
            bg-[var(--surface-2)] border border-[var(--border)]
            text-[var(--text)] placeholder-[var(--text-muted)]
            focus:outline-none focus:border-[var(--accent)]
            transition-colors disabled:opacity-50
          "
        />
      </div>

      <div>
        <label className="block text-xs tracking-widest uppercase text-[var(--text-muted)] mb-1.5">
          パスワード
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
          className="
            w-full px-4 py-3 rounded-lg text-sm
            bg-[var(--surface-2)] border border-[var(--border)]
            text-[var(--text)] placeholder-[var(--text-muted)]
            focus:outline-none focus:border-[var(--accent)]
            transition-colors disabled:opacity-50
          "
        />
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="
          mt-2 py-3 rounded-lg text-sm font-semibold tracking-widest uppercase
          bg-[var(--accent)] text-white
          hover:brightness-110 active:brightness-95
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-all
        "
      >
        {loading ? 'ログイン中...' : 'ログイン'}
      </button>
    </form>
  )
}

export default function LoginPage() {
  return (
    <div className="flex-1 flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1
            className="text-2xl font-black tracking-[0.12em] uppercase text-[var(--accent)] mb-1"
            style={{ fontFamily: 'var(--font-orbitron)' }}
          >
            LOGIN
          </h1>
          <p className="text-xs text-[var(--text-muted)] tracking-wide">
            解析履歴を保存するにはログインが必要です
          </p>
        </div>

        <Suspense fallback={<LoadingSpinner label="読み込み中" />}>
          <LoginForm />
        </Suspense>

        <p className="mt-6 text-center text-xs text-[var(--text-muted)]">
          アカウントをお持ちでない方は{' '}
          <Link href="/auth/signup" className="text-[var(--accent)] hover:underline">
            新規登録
          </Link>
        </p>
        <p className="mt-2 text-center text-xs text-[var(--text-muted)]">
          <Link href="/" className="hover:text-[var(--text)] transition-colors">
            ← ログインせずに使用する
          </Link>
        </p>
      </div>
    </div>
  )
}
