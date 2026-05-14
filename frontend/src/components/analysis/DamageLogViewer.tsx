'use client'

import { useEffect, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { StreamDamageEntry } from '@/hooks/useAnalysisStream'

interface DamageLogViewerProps {
  entries: StreamDamageEntry[]
  streaming: boolean
}

function formatTimestamp(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  const millis = ms % 1000
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
}

export function DamageLogViewer({ entries, streaming }: DamageLogViewerProps) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: entries.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 8,
  })

  useEffect(() => {
    if (streaming && entries.length > 0) {
      virtualizer.scrollToIndex(entries.length - 1, { behavior: 'smooth' })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries.length, streaming])

  if (entries.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--text-muted)] text-sm tracking-widest uppercase">
        解析待機中...
      </div>
    )
  }

  return (
    <div
      ref={parentRef}
      className="flex-1 overflow-auto"
      style={{ contain: 'strict' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const entry = entries[virtualRow.index]
          return (
            <div
              key={virtualRow.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
              className="flex items-center px-4 border-b border-[var(--border)] hover:bg-[var(--surface-2)] transition-colors"
            >
              <span
                className="w-28 shrink-0 text-xs text-[var(--text-muted)] tabular-nums"
                style={{ fontFamily: 'var(--font-share-tech-mono)' }}
              >
                {formatTimestamp(entry.timestamp_ms)}
              </span>
              <span className="mx-3 text-[var(--border-bright)]">|</span>
              <span
                className="text-sm tabular-nums font-semibold"
                style={{
                  fontFamily: 'var(--font-share-tech-mono)',
                  color: 'var(--accent)',
                  textShadow: '0 0 8px var(--accent-glow)',
                }}
              >
                +{entry.damage_value.toLocaleString()}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
