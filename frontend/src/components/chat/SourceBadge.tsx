'use client'
import { SourceChunk } from '@/types'
import { FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

interface Props { sources: SourceChunk[] }

export default function SourceBadge({ sources }: Props) {
  const [open, setOpen] = useState(false)

  if (!sources.length) return null

  const aCount = sources.filter(s => s.video_id === 'A').length
  const bCount = sources.filter(s => s.video_id === 'B').length

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-xs font-mono text-ghost hover:text-accent transition-colors"
      >
        <FileText size={11} />
        <span>
          {sources.length} source{sources.length !== 1 ? 's' : ''} cited
          {aCount > 0 && <span className="ml-1 text-signal">· {aCount}×A</span>}
          {bCount > 0 && <span className="ml-1 text-accent">· {bCount}×B</span>}
        </span>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((s, i) => (
            <div
              key={i}
              className={`rounded-lg border p-3 text-xs font-mono ${
                s.video_id === 'A'
                  ? 'border-signal/20 bg-signal/5'
                  : 'border-accent/20 bg-accent/5'
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`font-700 ${s.video_id === 'A' ? 'text-signal' : 'text-accent'}`}>
                  Video {s.video_id}
                </span>
                <span className="text-ghost">·</span>
                <span className="text-ghost">{s.platform}</span>
                <span className="text-ghost">·</span>
                <span className="text-ghost">chunk {s.chunk_index}</span>
                <span className="ml-auto text-ghost">score {s.score.toFixed(3)}</span>
              </div>
              <p className="text-ghost/80 leading-relaxed line-clamp-3">{s.chunk_text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
