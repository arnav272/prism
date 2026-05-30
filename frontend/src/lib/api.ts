import { IngestResponse, SourceChunk } from '@/types'

const BASE = '/api/v1'

export async function ingestVideos(
  youtubeUrl: string,
  instagramUrl: string
): Promise<IngestResponse> {
  const res = await fetch(`${BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url: youtubeUrl, instagram_url: instagramUrl }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Ingest failed: ${res.status}`)
  }
  return res.json()
}

export interface StreamEvent {
  type: 'sources' | 'token' | 'done' | 'error'
  content?: string
  data?: SourceChunk[]
  model?: string
}

export async function* streamChat(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[]
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, history }),
  })

  if (!res.ok || !res.body) {
    throw new Error(`Chat failed: ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') return
        try {
          yield JSON.parse(raw) as StreamEvent
        } catch {}
      }
    }
  }
}

export async function getRouterStatus() {
  const res = await fetch(`${BASE}/status`)
  return res.json()
}
