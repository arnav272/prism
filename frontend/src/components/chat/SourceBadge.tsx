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
    <div className="mt-3">
      <button onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-[10px] font-mono transition-colors"
        style={{ color: 'rgba(107,106,138,0.5)' }}
        onMouseEnter={e => (e.currentTarget.style.color = '#818cf8')}
        onMouseLeave={e => (e.currentTarget.style.color = 'rgba(107,106,138,0.5)')}>
        <FileText size={10} />
        <span>
          {sources.length} source{sources.length !== 1 ? 's' : ''} cited
          {aCount > 0 && <span style={{ color: '#818cf8' }}> · {aCount}×A</span>}
          {bCount > 0 && <span style={{ color: '#a855f7' }}> · {bCount}×B</span>}
        </span>
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {open && (
        <div className="mt-2.5 space-y-2">
          {sources.map((s, i) => (
            <div key={i} className="rounded-xl p-3 text-xs font-mono"
              style={{
                background: s.video_id === 'A' ? 'rgba(129,140,248,0.05)' : 'rgba(168,85,247,0.05)',
                border: `1px solid ${s.video_id === 'A' ? 'rgba(129,140,248,0.15)' : 'rgba(168,85,247,0.15)'}`,
              }}>
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span style={{ color: s.video_id === 'A' ? '#818cf8' : '#a855f7' }}>
                  Video {s.video_id}
                </span>
                <span style={{ color: '#6b6a8a' }}>· {s.platform} · chunk {s.chunk_index}</span>
                <span className="ml-auto" style={{ color: 'rgba(107,106,138,0.5)' }}>
                  {s.score.toFixed(3)}
                </span>
              </div>
              <p className="leading-relaxed line-clamp-3" style={{ color: 'rgba(107,106,138,0.7)' }}>
                {s.chunk_text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
