'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { signOut } from '@/lib/auth'

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { user } = useAuth()

  async function handleSignOut() {
    await signOut()
    router.push('/')
    router.refresh()
  }

  const navLink = (href: string, label: string) => (
    <Link
      href={href}
      className={`text-sm font-medium tracking-widest uppercase transition-colors ${
        pathname === href
          ? 'text-[var(--accent)]'
          : 'text-[var(--text-muted)] hover:text-[var(--text)]'
      }`}
    >
      {label}
    </Link>
  )

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span
              className="text-sm font-black tracking-[0.2em] uppercase text-[var(--accent)]"
              style={{ fontFamily: 'var(--font-orbitron)' }}
            >
              WILDS
            </span>
            <span className="hidden sm:block text-xs tracking-[0.15em] uppercase text-[var(--text-muted)]">
              DAMAGE ANALYZER
            </span>
          </Link>

          <nav className="flex items-center gap-6">
            {navLink('/', 'アップロード')}
            {user && navLink('/history', '履歴')}
            {user ? (
              <button
                onClick={handleSignOut}
                className="text-sm font-medium tracking-widest uppercase text-[var(--text-muted)] hover:text-[var(--danger)] transition-colors"
              >
                ログアウト
              </button>
            ) : (
              <Link
                href="/auth/login"
                className="text-sm font-medium tracking-widest uppercase px-3 py-1.5 border border-[var(--border)] rounded text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all"
              >
                ログイン
              </Link>
            )}
          </nav>
        </div>
      </div>
    </header>
  )
}
