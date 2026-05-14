import { UploadDropzone } from '@/components/upload/UploadDropzone'
import { VideoUrlInput } from '@/components/upload/VideoUrlInput'

export default function HomePage() {
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

        <div className="flex items-center gap-4">
          <div className="flex-1 h-px bg-[var(--border)]" />
          <span className="text-xs tracking-widest uppercase text-[var(--text-muted)]">または</span>
          <div className="flex-1 h-px bg-[var(--border)]" />
        </div>

        <VideoUrlInput />
      </div>
    </div>
  )
}
