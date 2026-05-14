export interface AnalysisSession {
  id: string
  user_id: string | null
  video_name: string
  video_source: 'file' | 'youtube'
  status: 'pending' | 'processing' | 'done' | 'error'
  total_damage: number | null
  max_damage: number | null
  avg_damage: number | null
  hit_count: number | null
  created_at: string
  completed_at: string | null
}

export interface DamageLog {
  id: string
  session_id: string
  timestamp_ms: number
  damage_value: number
  frame_index: number
}

export interface DamageSummary {
  total_damage: number
  max_damage: number
  avg_damage: number
  hit_count: number
}

export interface SSEDamageEvent {
  timestamp_ms: number
  damage_value: number
  progress: number
}

export interface SSEDoneEvent {
  total_damage: number
  max_damage: number
  avg_damage: number
  hit_count: number
}

export interface SSEErrorEvent {
  message: string
}

export type AnalysisStatus = 'connecting' | 'streaming' | 'done' | 'error'

export interface UploadResponse {
  session_id: string
  status: 'pending'
}

export interface PaginatedLogs {
  items: DamageLog[]
  total: number
  page: number
  page_size: number
}
