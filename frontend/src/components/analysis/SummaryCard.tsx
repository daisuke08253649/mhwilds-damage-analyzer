import type { DamageSummary } from '@/types'

interface SummaryCardProps {
  summary: DamageSummary | null
  entryCount: number
  streaming?: boolean
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 p-4 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
      <span className="text-xs tracking-widest uppercase text-[var(--text-muted)]">{label}</span>
      <span
        className="text-2xl font-bold tabular-nums text-[var(--text)]"
        style={{ fontFamily: 'var(--font-share-tech-mono)' }}
      >
        {value}
      </span>
    </div>
  )
}

export function SummaryCard({ summary, entryCount, streaming }: SummaryCardProps) {
  const totalDisplay = summary
    ? summary.total_damage.toLocaleString()
    : streaming
    ? '集計中...'
    : '---'

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-6 text-center">
        <p className="text-xs tracking-widest uppercase text-[var(--text-muted)] mb-2">
          TOTAL DAMAGE
        </p>
        <p
          className="text-5xl font-black tabular-nums"
          style={{
            fontFamily: 'var(--font-share-tech-mono)',
            color: 'var(--accent)',
            textShadow: '0 0 20px var(--accent-glow)',
          }}
        >
          {totalDisplay}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatItem
          label="最大"
          value={summary ? summary.max_damage.toLocaleString() : '---'}
        />
        <StatItem
          label="平均"
          value={summary ? Math.round(summary.avg_damage).toLocaleString() : '---'}
        />
        <StatItem
          label="ヒット数"
          value={
            summary
              ? summary.hit_count.toLocaleString()
              : streaming && entryCount > 0
              ? String(entryCount)
              : '---'
          }
        />
      </div>
    </div>
  )
}
