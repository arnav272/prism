export interface VideoMetadata {
  video_id: 'A' | 'B'
  platform: 'youtube' | 'instagram'
  url: string
  title: string
  creator: string
  follower_count: number | null
  views: number
  likes: number
  comments: number
  hashtags: string[]
  upload_date: string | null
  duration_seconds: number | null
  engagement_rate: number
  transcript_chunk_count: number
}

export interface IngestResponse {
  status: string
  session_id: string
  video_a: VideoMetadata
  video_b: VideoMetadata
  ingested_at: string
}

export interface SourceChunk {
  video_id: 'A' | 'B'
  platform: string
  chunk_text: string
  chunk_index: number
  score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  model_used?: string
  streaming?: boolean
}

export type AppState = 'idle' | 'ingesting' | 'ready' | 'error'
