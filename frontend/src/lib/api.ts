import type { AnalysisSession, DamageSummary, PaginatedLogs, UploadResponse } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

function authHeaders(token?: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function uploadFile(
  file: File,
  token?: string | null
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/api/v1/upload/file`, {
    method: 'POST',
    headers: authHeaders(token),
    body: formData,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? 'アップロードに失敗しました')
  }
  return res.json()
}

export async function uploadYouTube(
  url: string,
  token?: string | null
): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/v1/upload/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? 'YouTube URLの送信に失敗しました')
  }
  return res.json()
}

export async function getSessionSummary(
  sessionId: string,
  token?: string | null
): Promise<DamageSummary> {
  const res = await fetch(`${API_BASE}/api/v1/results/${sessionId}/summary`, {
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('サマリーの取得に失敗しました')
  return res.json()
}

export async function getSessionLogs(
  sessionId: string,
  page = 1,
  pageSize = 100,
  token?: string | null
): Promise<PaginatedLogs> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  const res = await fetch(`${API_BASE}/api/v1/results/${sessionId}/logs?${params}`, {
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('ログの取得に失敗しました')
  return res.json()
}

export async function exportSession(
  sessionId: string,
  format: 'csv' | 'json',
  token?: string | null
): Promise<void> {
  const params = new URLSearchParams({ format })
  const res = await fetch(`${API_BASE}/api/v1/results/${sessionId}/export?${params}`, {
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('エクスポートに失敗しました')

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `damage-${sessionId}.${format}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function getHistory(token: string): Promise<AnalysisSession[]> {
  const res = await fetch(`${API_BASE}/api/v1/history`, {
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('履歴の取得に失敗しました')
  return res.json()
}
