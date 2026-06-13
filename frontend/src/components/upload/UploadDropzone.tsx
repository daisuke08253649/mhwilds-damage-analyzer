'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useRouter } from 'next/navigation'
import { uploadFile } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

const ACCEPTED_TYPES = {
  'video/mp4': ['.mp4'],
  'video/quicktime': ['.mov'],
  'video/x-msvideo': ['.avi'],
}
const MAX_DURATION_MIN = 50

export function UploadDropzone() {
  const router = useRouter()
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0]
      if (!file) return

      setUploading(true)
      setUploadError(null)

      try {
        const token = await getAccessToken()
        const { session_id } = await uploadFile(file, token)
        router.push(`/analysis/${session_id}`)
      } catch (err) {
        setUploading(false)
        setUploadError(err instanceof Error ? err.message : 'アップロードに失敗しました')
      }
    },
    [router]
  )

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    disabled: uploading,
  })

  const rejectionError =
    fileRejections[0]?.errors[0]?.message ?? null

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          relative group cursor-pointer rounded-lg border-2 border-dashed p-12 text-center
          transition-all duration-200 outline-none
          ${isDragActive
            ? 'border-[var(--accent)] bg-[var(--accent-dim)]'
            : 'border-[var(--border-bright)] hover:border-[var(--accent)] hover:bg-[var(--accent-dim)]'
          }
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <div className="flex flex-col items-center gap-4">
            <LoadingSpinner size="lg" />
            <p className="text-sm tracking-widest uppercase text-[var(--text-muted)]">
              アップロード中...
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div
              className={`text-5xl transition-transform duration-200 ${
                isDragActive ? 'scale-110' : 'group-hover:scale-105'
              }`}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="w-16 h-16 mx-auto"
                stroke={isDragActive ? 'var(--accent)' : 'var(--text-muted)'}
                strokeWidth={1.5}
              >
                <path
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <p
                className={`text-base font-semibold tracking-wide ${
                  isDragActive ? 'text-[var(--accent)]' : 'text-[var(--text)]'
                }`}
              >
                {isDragActive ? 'ドロップしてアップロード' : 'ここにドラッグ＆ドロップ'}
              </p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                またはクリックしてファイルを選択
              </p>
            </div>
            <p className="text-xs text-[var(--text-muted)] tracking-wide">
              MP4 / MOV / AVI — 最大 {MAX_DURATION_MIN} 分
            </p>
          </div>
        )}
      </div>

      {(rejectionError || uploadError) && (
        <p className="mt-3 text-sm text-[var(--danger)] text-center">
          {uploadError ?? rejectionError}
        </p>
      )}
    </div>
  )
}
