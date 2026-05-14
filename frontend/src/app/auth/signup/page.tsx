'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { signUp } from '@/lib/auth'

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('パスワードは8文字以上で設定してください')
      return
    }

    setLoading(true)
    const result = await signUp(email, password)
    setLoading(false)

    if ('error' in result) {
      setError(result.error)
      return
    }

    if (!result.user?.email_confirmed_at) {
      setDone(true)
    } else {
      router.push('/')
      router.refresh()
    }
  }

  if (done) {
    return (
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-sm text-center">
          <div className="text-4xl mb-4 text-[var(--success)]">✓</div>
          <h2
            className="text-xl font-bold tracking-widest uppercase text-[var(--text)] mb-2"
            style={{ fontFamily: 'var(--font-orbitron)' }}
          >
            確認メールを送信しました
          </h2>
          <p className="text-sm text-[var(--text-muted)] mb-6">
            {email} に確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。
          </p>
          <Link
            href="/auth/login"
            className="text-sm text-[var(--accent)] hover:underline"
          >
            ログインページへ
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1
            className="text-2xl font-black tracking-[0.12em] uppercase text-[var(--accent)] mb-1"
            style={{ fontFamily: 'var(--font-orbitron)' }}
          >
            SIGN UP
          </h1>
          <p className="text-xs text-[var(--text-muted)] tracking-wide">
            無料アカウントで解析履歴を保存
          </p>
        </div>

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
              パスワード（8文字以上）
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
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

          {error && (
            <p className="text-sm text-[var(--danger)]">{error}</p>
          )}

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
            {loading ? '登録中...' : 'アカウント作成'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-[var(--text-muted)]">
          すでにアカウントをお持ちの方は{' '}
          <Link href="/auth/login" className="text-[var(--accent)] hover:underline">
            ログイン
          </Link>
        </p>
      </div>
    </div>
  )
}
