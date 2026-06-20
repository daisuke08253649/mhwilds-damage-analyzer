import React from 'react'
import { UploadDropzone } from '@/components/upload/UploadDropzone'

export default function HomePage(): React.JSX.Element {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-xl flex flex-col gap-10">
        <div className="text-center">
          <h1
            className="text-4xl font-black tracking-[0.12em] uppercase text-[var(--accent)] mb-2"
            style={{ fontFamily: 'var(--font-orbitron)' }}
          >
            DAMAGE ANALYZER
          </h1>
          <p className="text-sm text-[var(--text-muted)] tracking-wide">
            Monster Hunter Wilds の動画をアップロードしてダメージを解析
          </p>
        </div>

        <UploadDropzone />
      </div>
    </div>
  )
}
