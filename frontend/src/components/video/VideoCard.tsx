'use client'
import { VideoMetadata } from '@/types'
import { Eye, Heart, MessageCircle, Users, Clock, Calendar, Hash, TrendingUp, AlertTriangle } from 'lucide-react'

interface Props { video: VideoMetadata; label: string }

function fmt(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000)     return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)         return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

function fmtDuration(raw: number | string | null | undefined): string {
  if (raw === null || raw === undefined) return '—'
  let s: number
  if (typeof raw === 'string') {
    const parts = raw.split(':').map(p => parseFloat(p))
    s = parts.length === 3 ? parts[0]*3600+parts[1]*60+parts[2]
      : parts.length === 2 ? parts[0]*60+parts[1]
      : parseFloat(raw)
  } else { s = raw }
  if (isNaN(s)) return '—'
  const t = Math.floor(s), h = Math.floor(t/3600), m = Math.floor((t%3600)/60), sec = t%60
  return h > 0
    ? `${h}:${m.toString().padStart(2,'0')}:${sec.toString().padStart(2,'0')}`
    : `${m}:${sec.toString().padStart(2,'0')}`
}

function fmtDate(d: string | null): string {
  if (!d) return '—'
  if (d.length === 8) return `${d.slice(0,4)}-${d.slice(4,6)}-${d.slice(6,8)}`
  return d
}

// ── Title cleaner ─────────────────────────────────────────────────
// Fixes "Video by nasa", "video by youtube", generic fallback titles
function cleanTitle(title: string, creator: string, platform: string): string {
  const lower = title.toLowerCase().trim()

  const genericPatterns = [
    /^video by .+$/i,
    /^instagram reel$/i,
    /^reel by .+$/i,
    /^youtube video$/i,
    /^untitled$/i,
    /^media stream$/i,
  ]

  const isGeneric = genericPatterns.some(p => p.test(lower)) || title.length < 6

  if (isGeneric) {
    const platformLabel = platform === 'youtube' ? 'YouTube' : 'Instagram Reel'
    const creatorLabel  = creator && creator !== 'Unknown' && creator !== 'Unknown Creator'
      ? creator
      : platformLabel
    return `${creatorLabel} · ${platformLabel}`
  }

  return title
}

export default function VideoCard({ video, label }: Props) {
  const isYT    = video.platform === 'youtube'
  const noViews = (!video.views || video.views === 0) && (video.likes > 0 || video.comments > 0)
  const engValid = video.views > 0

  const platformColor = isYT ? '#818cf8' : '#a855f7'
  const engColor = !engValid ? '#6b6a8a'
    : video.engagement_rate > 5  ? '#c4b5fd'
    : video.engagement_rate > 2  ? '#818cf8'
    : '#6b6a8a'

  const displayTitle = cleanTitle(video.title, video.creator, video.platform)

  return (
    <div className="liquid-glass rounded-2xl overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.02)' }}>

      {/* 1px gradient accent line */}
      <div className="h-px w-full"
        style={{ background: `linear-gradient(to right, transparent, ${platformColor}60, transparent)` }} />

      <div className="p-4 sm:p-6">
        {/* Label row */}
        <div className="flex items-center justify-between mb-4 sm:mb-5">
          <span className="font-mono text-[10px] tracking-[0.15em] uppercase" style={{ color: '#6b6a8a' }}>
            Video {label}
          </span>
          <span className="text-[10px] font-mono px-2.5 py-1 rounded-full"
            style={{ color: platformColor, background: `${platformColor}12`, border: `1px solid ${platformColor}25` }}>
            {isYT ? 'YouTube' : 'Instagram'}
          </span>
        </div>

        {/* Title — cleaned */}
        <h3 className="font-display font-semibold text-sm sm:text-base leading-snug mb-2 line-clamp-2"
          style={{ color: '#eeedf5' }}>
          {displayTitle}
        </h3>

        {/* Creator */}
        <div className="flex items-center gap-1.5 mb-5 sm:mb-6 flex-wrap">
          <Users size={11} style={{ color: '#6b6a8a' }} />
          <span className="text-xs font-mono" style={{ color: '#6b6a8a' }}>{video.creator}</span>
          {video.follower_count && (
            <span className="text-xs" style={{ color: '#6b6a8a' }}>· {fmt(video.follower_count)} followers</span>
          )}
        </div>

        {/* Engagement */}
        <div className="rounded-2xl p-3.5 sm:p-4 mb-4 sm:mb-5"
          style={{ background: 'rgba(129,140,248,0.05)', border: '1px solid rgba(129,140,248,0.1)' }}>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={12} style={{ color: engColor }} />
            <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: '#6b6a8a' }}>
              Engagement Rate
            </span>
          </div>

          {engValid ? (
            <span className="font-display font-semibold text-3xl sm:text-4xl" style={{ color: engColor }}>
              {video.engagement_rate.toFixed(2)}
              <span className="text-xl sm:text-2xl" style={{ color: `${engColor}80` }}>%</span>
            </span>
          ) : noViews ? (
            <div>
              <div className="flex items-start gap-2">
                <AlertTriangle size={12} style={{ color: '#6b6a8a', marginTop: 2, flexShrink: 0 }} />
                <div>
                  <p className="font-display text-sm font-medium" style={{ color: '#6b6a8a' }}>Incalculable</p>
                </div>
              </div>
              {/* Explanatory note — owns the limitation confidently */}
              <p className="text-[10px] font-mono leading-relaxed mt-2"
                style={{ color: 'rgba(107,106,138,0.55)', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 8 }}>
                Note: Instagram natively restricts view metrics via public API.
                Platform engagement rates use fallback estimation models.
              </p>
            </div>
          ) : (
            <span className="font-display text-xl font-semibold" style={{ color: '#6b6a8a' }}>No data</span>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 sm:gap-2.5 mb-4 sm:mb-5">
          {[
            { icon: Eye,           label: 'Views',    val: noViews ? null : fmt(video.views) },
            { icon: Heart,         label: 'Likes',    val: fmt(video.likes) },
            { icon: MessageCircle, label: 'Comments', val: fmt(video.comments) },
          ].map(({ icon: Icon, label: l, val }) => (
            <div key={l} className="rounded-xl p-2.5 sm:p-3 text-center"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
              <Icon size={11} style={{ color: '#6b6a8a', margin: '0 auto 5px' }} />
              <div className="font-display font-semibold text-xs sm:text-sm" style={{ color: '#eeedf5' }}>
                {val ?? <span style={{ color: 'rgba(107,106,138,0.5)', fontSize: 10 }}>N/A</span>}
              </div>
              <div className="text-[9px] sm:text-[10px] font-mono mt-0.5" style={{ color: '#6b6a8a' }}>{l}</div>
            </div>
          ))}
        </div>

        {/* Meta strip */}
        <div className="flex items-center gap-3 sm:gap-4 flex-wrap"
          style={{ color: '#6b6a8a', fontSize: 10, fontFamily: 'DM Mono, monospace' }}>
          <span className="flex items-center gap-1"><Clock size={9} />{fmtDuration(video.duration_seconds)}</span>
          <span className="flex items-center gap-1"><Calendar size={9} />{fmtDate(video.upload_date)}</span>
          <span className="flex items-center gap-1"><Hash size={9} />{video.transcript_chunk_count} chunks</span>
        </div>

        {/* Hashtags */}
        {video.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 sm:mt-4">
            {video.hashtags.slice(0,5).map(tag => (
              <span key={tag}
                className="text-[10px] font-mono px-2 py-0.5 rounded-full"
                style={{ color: '#6b6a8a', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                {tag.startsWith('#') ? tag : `#${tag}`}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
