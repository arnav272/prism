'use client'
import { useState } from 'react'
import { Prism, RotateCcw, Activity } from 'lucide-react'
import { IngestResponse, AppState } from '@/types'
import IngestForm from '@/components/ui/IngestForm'
import VideoCard from '@/components/video/VideoCard'
import ChatPanel from '@/components/chat/ChatPanel'

export default function Home() {
  const [appState, setAppState] = useState<AppState>('idle')
  const [ingestData, setIngestData] = useState<IngestResponse | null>(null)

  function handleIngestSuccess(data: IngestResponse) {
    setIngestData(data)
    setAppState('ready')
  }

  function reset() {
    setIngestData(null)
    setAppState('idle')
  }

  return (
    <main className="min-h-screen bg-ink text-text">
      {/* ── NAV ──────────────────────────────── */}
      <nav className="border-b border-border px-6 py-4 flex items-center justify-between sticky top-0 bg-ink/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
            <Activity size={14} className="text-ink" strokeWidth={2.5} />
          </div>
          <span className="font-display font-800 text-base tracking-tight text-text">PRISM</span>
          <span className="text-xs font-mono text-ghost/60 hidden sm:block">
            Content Intelligence
          </span>
        </div>

        <div className="flex items-center gap-4">
          {appState === 'ready' && ingestData && (
            <span className="text-xs font-mono text-ghost hidden sm:block">
              session <span className="text-accent">{ingestData.session_id.slice(0, 8)}…</span>
            </span>
          )}
          {appState === 'ready' && (
            <button
              onClick={reset}
              className="flex items-center gap-1.5 text-xs font-mono text-ghost hover:text-accent transition-colors"
            >
              <RotateCcw size={12} />
              New session
            </button>
          )}
        </div>
      </nav>

      {/* ── IDLE: Hero + Form ──────────────── */}
      {appState === 'idle' && (
        <section className="flex flex-col items-center justify-center min-h-[85vh] px-6 text-center">
          {/* Decorative background glow */}
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-signal/5 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 space-y-8 w-full max-w-xl">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 border border-border rounded-full px-4 py-1.5 text-xs font-mono text-ghost mx-auto">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              RAG-Powered · Gemini + Groq · Qdrant
            </div>

            {/* Headline */}
            <div>
              <h1 className="font-display font-800 text-5xl sm:text-6xl tracking-tight text-text leading-none mb-3">
                Break down<br />
                <span className="text-accent">any video.</span>
              </h1>
              <p className="text-ghost text-base font-body max-w-sm mx-auto leading-relaxed">
                Paste a YouTube and Instagram URL. PRISM extracts transcripts, computes engagement, and lets you ask anything.
              </p>
            </div>

            {/* Form */}
            <IngestForm onSuccess={handleIngestSuccess} />

            {/* Dividers */}
            <div className="flex items-center gap-4 text-xs font-mono text-ghost/40">
              <div className="flex-1 h-px bg-border" />
              <span>YouTube · Instagram Reels</span>
              <div className="flex-1 h-px bg-border" />
            </div>
          </div>
        </section>
      )}

      {/* ── READY: Dashboard ──────────────── */}
      {appState === 'ready' && ingestData && (
        <section className="p-6 animate-fade-up">
          {/* Top row: session info */}
          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px bg-border" />
            <span className="text-xs font-mono text-ghost whitespace-nowrap">
              {ingestData.video_a.transcript_chunk_count + ingestData.video_b.transcript_chunk_count} chunks indexed
              · {new Date(ingestData.ingested_at).toLocaleTimeString()}
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* Main layout: cards left, chat right */}
          <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 max-w-7xl mx-auto">
            {/* Left: video cards stacked */}
            <div className="space-y-4">
              <VideoCard video={ingestData.video_a} label="A" />
              <VideoCard video={ingestData.video_b} label="B" />
            </div>

            {/* Right: chat panel — fills remaining height */}
            <div className="lg:sticky lg:top-[73px] lg:h-[calc(100vh-100px)]">
              <ChatPanel sessionId={ingestData.session_id} />
            </div>
          </div>
        </section>
      )}
    </main>
  )
}
