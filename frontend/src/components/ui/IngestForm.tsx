'use client'
import { useState, FormEvent } from 'react'
import { Youtube, Instagram, Loader2, Zap } from 'lucide-react'
import { ingestVideos } from '@/lib/api'
import { IngestResponse } from '@/types'

interface Props {
  onSuccess: (data: IngestResponse) => void
}

export default function IngestForm({ onSuccess }: Props) {
  const [ytUrl, setYtUrl] = useState('')
  const [igUrl, setIgUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState('')

  const STAGES = [
    'Fetching YouTube transcript…',
    'Pulling Instagram metadata…',
    'Chunking transcripts…',
    'Embedding into Qdrant…',
    'Finalising session…',
  ]

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!ytUrl.trim() || !igUrl.trim()) return

    setLoading(true)
    setError(null)

    let si = 0
    const interval = setInterval(() => {
      setStage(STAGES[si % STAGES.length])
      si++
    }, 1800)

    try {
      const data = await ingestVideos(ytUrl.trim(), igUrl.trim())
      onSuccess(data)
    } catch (e: any) {
      setError(e.message || 'Ingest failed. Check URLs and try again.')
    } finally {
      clearInterval(interval)
      setLoading(false)
      setStage('')
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto animate-fade-up">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* YouTube */}
        <div className="flex items-center gap-3 bg-panel border border-border rounded-xl px-4 py-3 focus-within:border-signal/50 transition-colors">
          <Youtube size={16} className="text-signal flex-shrink-0" />
          <input
            type="url"
            value={ytUrl}
            onChange={e => setYtUrl(e.target.value)}
            placeholder="YouTube video URL"
            required
            disabled={loading}
            className="flex-1 bg-transparent text-sm text-text placeholder-ghost outline-none font-mono"
          />
        </div>

        {/* Instagram */}
        <div className="flex items-center gap-3 bg-panel border border-border rounded-xl px-4 py-3 focus-within:border-accent/50 transition-colors">
          <Instagram size={16} className="text-accent flex-shrink-0" />
          <input
            type="url"
            value={igUrl}
            onChange={e => setIgUrl(e.target.value)}
            placeholder="Instagram Reel URL"
            required
            disabled={loading}
            className="flex-1 bg-transparent text-sm text-text placeholder-ghost outline-none font-mono"
          />
        </div>

        {error && (
          <p className="text-xs font-mono text-signal bg-signal/10 border border-signal/20 rounded-lg px-4 py-2.5">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading || !ytUrl.trim() || !igUrl.trim()}
          className="w-full flex items-center justify-center gap-2.5 bg-accent text-ink font-display font-700 text-sm rounded-xl py-3.5 hover:bg-accent-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              <span className="font-mono text-xs">{stage || 'Processing…'}</span>
            </>
          ) : (
            <>
              <Zap size={15} />
              Analyse Videos
            </>
          )}
        </button>
      </form>
    </div>
  )
}
