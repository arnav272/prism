'use client'
import { VideoMetadata } from '@/types'
import { Eye, Heart, MessageCircle, Users, Clock, Calendar, Hash, TrendingUp } from 'lucide-react'

interface Props {
  video: VideoMetadata
  label: string
}

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

function fmtDuration(s: number | null): string {
  if (!s) return '—'
  const m = Math.floor(s / 60), sec = s % 60
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export default function VideoCard({ video, label }: Props) {
  const isYT = video.platform === 'youtube'
  const engColor = video.engagement_rate > 5 ? 'text-accent' : video.engagement_rate > 2 ? 'text-sky' : 'text-ghost'

  return (
    <div className="relative rounded-2xl border border-border bg-panel overflow-hidden animate-fade-up">
      {/* Header stripe */}
      <div className={`h-1 w-full ${isYT ? 'bg-signal' : 'bg-accent'}`} />

      <div className="p-5">
        {/* Label + Platform */}
        <div className="flex items-center justify-between mb-4">
          <span className="font-display text-xs font-700 tracking-widest uppercase text-ghost">
            Video {label}
          </span>
          <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${
            isYT
              ? 'border-signal/30 text-signal bg-signal/10'
              : 'border-accent/30 text-accent bg-accent/10'
          }`}>
            {isYT ? 'YouTube' : 'Instagram'}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-display font-700 text-sm text-text leading-snug mb-1 line-clamp-2">
          {video.title}
        </h3>

        {/* Creator */}
        <div className="flex items-center gap-1.5 mb-5">
          <Users size={11} className="text-ghost" />
          <span className="text-xs text-ghost font-mono">{video.creator}</span>
          {video.follower_count && (
            <span className="text-xs text-ghost">· {fmt(video.follower_count)} followers</span>
          )}
        </div>

        {/* Engagement Rate — hero metric */}
        <div className="mb-5 p-3 rounded-xl bg-ink border border-border">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp size={13} className={engColor} />
            <span className="text-xs text-ghost font-mono uppercase tracking-wider">Engagement Rate</span>
          </div>
          <span className={`font-display text-3xl font-800 ${engColor}`}>
            {video.engagement_rate.toFixed(2)}%
          </span>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          {[
            { icon: Eye,            val: fmt(video.views),    label: 'Views' },
            { icon: Heart,          val: fmt(video.likes),    label: 'Likes' },
            { icon: MessageCircle,  val: fmt(video.comments), label: 'Comments' },
          ].map(({ icon: Icon, val, label: l }) => (
            <div key={l} className="rounded-lg bg-ink border border-border p-2.5 text-center">
              <Icon size={12} className="text-ghost mx-auto mb-1" />
              <div className="font-display font-700 text-sm text-text">{val}</div>
              <div className="text-xs text-ghost font-mono">{l}</div>
            </div>
          ))}
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 text-xs text-ghost font-mono">
          <span className="flex items-center gap-1">
            <Clock size={10} />{fmtDuration(video.duration_seconds)}
          </span>
          {video.upload_date && (
            <span className="flex items-center gap-1">
              <Calendar size={10} />
              {video.upload_date.slice(0, 4)}-{video.upload_date.slice(4, 6)}-{video.upload_date.slice(6, 8)}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Hash size={10} />{video.transcript_chunk_count} chunks
          </span>
        </div>

        {/* Hashtags */}
        {video.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {video.hashtags.slice(0, 6).map((tag) => (
              <span key={tag} className="text-xs font-mono text-ghost bg-muted px-2 py-0.5 rounded-full">
                {tag.startsWith('#') ? tag : `#${tag}`}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
