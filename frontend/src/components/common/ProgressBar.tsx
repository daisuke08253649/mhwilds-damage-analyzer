interface ProgressBarProps {
  value: number
  label?: string
  showPercent?: boolean
}

export function ProgressBar({ value, label, showPercent = true }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value))

  return (
    <div className="w-full">
      {(label || showPercent) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && (
            <span className="text-xs tracking-widest uppercase text-[var(--text-muted)]">
              {label}
            </span>
          )}
          {showPercent && (
            <span
              className="text-xs tabular-nums text-[var(--accent)]"
              style={{ fontFamily: 'var(--font-share-tech-mono)' }}
            >
              {clamped.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      <div className="h-1.5 w-full rounded-full bg-[var(--surface-2)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{
            width: `${clamped}%`,
            background: 'linear-gradient(90deg, var(--accent) 0%, #fb923c 100%)',
            boxShadow: '0 0 8px var(--accent-glow)',
          }}
        />
      </div>
    </div>
  )
}
