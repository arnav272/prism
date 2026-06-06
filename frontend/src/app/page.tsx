'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { RotateCcw, Zap, BarChart2, MessageSquare, Layers, ChevronDown, ChevronUp, Menu, X } from 'lucide-react'
import { IngestResponse, AppState } from '@/types'
import IngestForm from '@/components/ui/IngestForm'
import VideoCard from '@/components/video/VideoCard'
import ChatPanel from '@/components/chat/ChatPanel'

const FAQ = [
  {
    q: 'How does the system process content without getting rate-limited by platform security?',
    a: "PRISM features a dual-track ingestion engine. Lane 1 hits optimized transcription endpoints natively, while Lane 2 spins up an isolated Python subprocess sandbox that downloads raw media audio and feeds it directly into AssemblyAI's speech-to-text pipeline as a bulletproof fallback.",
  },
  {
    q: 'What handles the vector search and context retrieval layers?',
    a: 'Dense contextual embeddings are cataloged and searched natively inside a localized Qdrant database instance. This handles sub-second semantic retrieval during live streaming chat queries.',
  },
  {
    q: 'Can this pipeline analyze uncaptioned reels or short-form clips?',
    a: 'Yes. By executing our speech-to-text audio pipeline fallback, the backend synthesizes fully timestamped text records out of raw video audio, rendering uncaptioned clips completely searchable via our LLM context router.',
  },
]

const TECH_PILLS = [
  { label: 'Gemini 2.5 Flash', color: '#818cf8' },
  { label: 'Groq Inference',   color: '#a855f7' },
  { label: 'Qdrant Vector DB', color: '#34d399' },
  { label: 'AssemblyAI STT',   color: '#ff6b35' },
  { label: 'LangChain RAG',    color: '#f472b6' },
]

function FaqAccordion() {
  const [open, setOpen] = useState<number | null>(null)
  return (
    <div className="space-y-3">
      {FAQ.map((item, i) => (
        <div key={i} className="liquid-glass rounded-2xl overflow-hidden">
          <button
            onClick={() => setOpen(open === i ? null : i)}
            className="w-full flex items-center justify-between px-5 py-4 sm:px-6 sm:py-5 text-left transition-colors hover:bg-white/[0.02]"
          >
            <span className="font-display font-medium text-sm pr-6 leading-relaxed" style={{ color: '#eeedf5' }}>
              {item.q}
            </span>
            {open === i
              ? <ChevronUp size={15} style={{ color: '#6b6a8a', flexShrink: 0 }} />
              : <ChevronDown size={15} style={{ color: '#6b6a8a', flexShrink: 0 }} />
            }
          </button>
          {open === i && (
            <div className="px-5 pb-5 sm:px-6">
              <div className="h-px w-full mb-4" style={{ background: 'rgba(255,255,255,0.06)' }} />
              <p className="text-sm leading-relaxed font-mono" style={{ color: '#b0afc8' }}>{item.a}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Background video hook — safe remount on every call ────────────
function useVideoFade(active: boolean) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const rafRef   = useRef<number>(0)

  const startVideo = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    cancelAnimationFrame(rafRef.current)
    video.style.opacity = '0'
    video.currentTime = 0

    function fadeLoop() {
      if (!video) return
      const dur = video.duration || 1
      const t   = video.currentTime
      const ft  = 0.5
      if (t < ft)          video.style.opacity = String(t / ft)
      else if (t > dur-ft) video.style.opacity = String((dur - t) / ft)
      else                 video.style.opacity = '1'
      rafRef.current = requestAnimationFrame(fadeLoop)
    }

    function onEnded() {
      if (!video) return
      video.style.opacity = '0'
      cancelAnimationFrame(rafRef.current)
      setTimeout(() => {
        video.currentTime = 0
        video.play().catch(() => {})
        rafRef.current = requestAnimationFrame(fadeLoop)
      }, 100)
    }

    video.removeEventListener('ended', onEnded)
    video.addEventListener('ended', onEnded)
    video.play().catch(() => {})
    rafRef.current = requestAnimationFrame(fadeLoop)

    return () => {
      cancelAnimationFrame(rafRef.current)
      video.removeEventListener('ended', onEnded)
    }
  }, [])

  useEffect(() => {
    if (!active) return
    // Small delay ensures DOM is fully painted after state transition
    const t = setTimeout(startVideo, 80)
    return () => clearTimeout(t)
  }, [active, startVideo])

  return videoRef
}

// ── Mobile nav drawer ─────────────────────────────────────────────
function MobileNav({ onLaunch }: { onLaunch: () => void }) {
  const [open, setOpen] = useState(false)
  const links = ['About', 'Capabilities', 'FAQ']

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        className="md:hidden liquid-glass w-9 h-9 rounded-xl flex items-center justify-center"
        aria-label="Toggle navigation"
      >
        {open ? <X size={15} style={{ color: '#eeedf5' }} /> : <Menu size={15} style={{ color: '#eeedf5' }} />}
      </button>

      {open && (
        <div
          className="absolute top-full left-0 right-0 mx-4 mt-2 rounded-2xl overflow-hidden z-50 liquid-glass md:hidden"
          style={{ background: 'rgba(7,6,15,0.95)', backdropFilter: 'blur(24px)', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <div className="p-3 space-y-1">
            {links.map(label => (
              <a
                key={label}
                href={`#${label.toLowerCase()}`}
                onClick={() => setOpen(false)}
                className="block px-4 py-3 rounded-xl text-sm transition-colors hover:bg-white/[0.04]"
                style={{ color: 'rgba(238,237,245,0.7)', textDecoration: 'none' }}
              >
                {label}
              </a>
            ))}
            <div className="h-px my-2" style={{ background: 'rgba(255,255,255,0.06)' }} />
            <button
              onClick={() => { setOpen(false); onLaunch() }}
              className="w-full text-left px-4 py-3 rounded-xl text-sm transition-colors hover:bg-white/[0.04]"
              style={{ color: '#818cf8' }}
            >
              Try it free ↓
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default function Home() {
  const [appState, setAppState]     = useState<AppState>('idle')
  const [ingestData, setIngestData] = useState<IngestResponse | null>(null)
  const [dashReady, setDashReady]   = useState(false)

  const isLanding  = appState === 'idle'
  const videoRef   = useVideoFade(isLanding)

  function handleIngestSuccess(data: IngestResponse) {
    setIngestData(data)
    setDashReady(false)
    setAppState('ready')
    // Skeleton fades out after 400ms
    setTimeout(() => setDashReady(true), 400)
  }

  function reset() {
    setIngestData(null)
    setDashReady(false)
    setAppState('idle')
    // Video restarts via useVideoFade watching isLanding
  }

  function scrollToForm() {
    document.getElementById('analyse')?.scrollIntoView({ behavior: 'smooth' })
  }

  // ── DASHBOARD ───────────────────────────────────────────────────
  if (appState === 'ready' && ingestData) {
    return (
      <main className="min-h-screen" style={{ background: '#07060f', color: '#eeedf5' }}>

        {/* Dashboard nav */}
        <nav className="px-4 sm:px-8 py-4 sm:py-5 flex items-center justify-between sticky top-0 z-50"
          style={{ background: 'rgba(7,6,15,0.88)', backdropFilter: 'blur(24px)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center liquid-glass">
              <BarChart2 size={13} style={{ color: '#eeedf5' }} strokeWidth={2.5} />
            </div>
            <span className="font-display font-semibold text-base tracking-tight" style={{ color: '#eeedf5' }}>PRISM</span>
            <span className="text-xs font-mono hidden sm:block" style={{ color: '#6b6a8a' }}>/ Analytics</span>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="hidden sm:flex items-center gap-2 liquid-glass rounded-full px-3 py-1.5">
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#818cf8' }} />
              <span className="text-[10px] font-mono" style={{ color: '#6b6a8a' }}>
                {ingestData.session_id.slice(0,8)}…
              </span>
            </div>
            <span className="text-[10px] font-mono hidden lg:block px-3 py-1.5 rounded-full"
              style={{ color: '#6b6a8a', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
              {ingestData.video_a.transcript_chunk_count + ingestData.video_b.transcript_chunk_count} chunks indexed
            </span>
            <button onClick={reset}
              className="liquid-glass flex items-center gap-1.5 text-xs font-mono rounded-full px-3 sm:px-4 py-2 transition-all hover:bg-white/[0.04]"
              style={{ color: '#eeedf5' }}>
              <RotateCcw size={11} />
              <span className="hidden sm:inline">New Analysis</span>
            </button>
          </div>
        </nav>

        {/* Skeleton → Dashboard transition */}
        {!dashReady ? (
          <div className="p-4 sm:p-6 max-w-[1600px] mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] xl:grid-cols-[420px_1fr] gap-4 sm:gap-5 mt-2">
              <div className="space-y-4">
                <SkeletonCard />
                <SkeletonCard />
              </div>
              <SkeletonChat />
            </div>
          </div>
        ) : (
          <section
            className="p-4 sm:p-6 max-w-[1600px] mx-auto animate-fade-up"
            style={{ opacity: 0, animationFillMode: 'forwards' }}
          >
            <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] xl:grid-cols-[420px_1fr] gap-4 sm:gap-5 mt-2">
              <div className="space-y-4">
                <VideoCard video={ingestData.video_a} label="A" />
                <VideoCard video={ingestData.video_b} label="B" />
              </div>
              <div className="lg:sticky lg:top-[73px] lg:h-[calc(100vh-100px)]">
                <ChatPanel sessionId={ingestData.session_id} />
              </div>
            </div>
          </section>
        )}
      </main>
    )
  }

  // ── LANDING ─────────────────────────────────────────────────────
  return (
    <div style={{ background: '#07060f', color: '#eeedf5' }}>

      {/* Hero */}
      <div className="relative min-h-screen overflow-hidden flex flex-col">

        {/* BG video — key prop forces remount on landing return */}
        <video
          key="hero-video"
          ref={videoRef}
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260328_065045_c44942da-53c6-4804-b734-f9e07fc22e08.mp4"
          muted playsInline
          className="absolute inset-0 w-full h-full object-cover pointer-events-none"
          style={{ opacity: 0, zIndex: 0 }}
        />

        {/* Blur blob */}
        <div className="absolute pointer-events-none hidden sm:block"
          style={{ width: '70vw', maxWidth: 984, height: '50vh', maxHeight: 527, top: '50%', left: '50%', transform: 'translate(-50%,-50%)', background: 'rgba(3,2,10,0.92)', filter: 'blur(82px)', opacity: 0.9, zIndex: 1 }} />

        <div className="relative flex flex-col min-h-screen" style={{ zIndex: 2 }}>

          {/* Navbar */}
          <nav className="relative w-full py-4 sm:py-5 px-4 sm:px-8 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center liquid-glass">
                <BarChart2 size={15} style={{ color: '#eeedf5' }} strokeWidth={2.5} />
              </div>
              <span className="font-display font-semibold text-lg tracking-tight">PRISM</span>
            </div>

            {/* Desktop nav links */}
            <div className="hidden md:flex items-center gap-1">
              {['About', 'Capabilities', 'FAQ'].map(label => (
                <a key={label} href={`#${label.toLowerCase()}`}
                  className="px-4 py-2 text-sm rounded-lg transition-all hover:bg-white/[0.04]"
                  style={{ color: 'rgba(238,237,245,0.55)', textDecoration: 'none' }}
                  onMouseEnter={e => (e.currentTarget.style.color = '#eeedf5')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'rgba(238,237,245,0.55)')}>
                  {label}
                </a>
              ))}
            </div>

            <div className="flex items-center gap-2">
              {/* Desktop CTA */}
              <a href="#analyse"
                className="hidden md:inline-flex liquid-glass rounded-full px-5 py-2 text-sm font-medium transition-all hover:bg-white/[0.04] hover:scale-[1.02]"
                style={{ color: '#fdfcfb', textDecoration: 'none' }}>
                Try it free
              </a>
              {/* Mobile hamburger */}
              <MobileNav onLaunch={scrollToForm} />
            </div>
          </nav>

          <div className="h-px mx-4 sm:mx-8 flex-shrink-0"
            style={{ background: 'linear-gradient(to right, transparent, rgba(238,237,245,0.08), transparent)' }} />

          {/* Hero content */}
          <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-8 text-center py-12">
            <div className="liquid-glass rounded-full px-4 py-1.5 flex items-center gap-2 mb-6 sm:mb-8 animate-fade-up"
              style={{ animationDelay: '0.1s', opacity: 0 }}>
              <Zap size={11} style={{ color: '#818cf8' }} />
              <span className="text-xs font-mono tracking-wider" style={{ color: 'rgba(238,237,245,0.55)' }}>
                RAG-Powered · Gemini 2.5 + Groq · Qdrant
              </span>
            </div>

            <div className="animate-fade-up" style={{ animationDelay: '0.2s', opacity: 0 }}>
              <h1 className="font-display font-normal leading-[1.02] tracking-[-0.024em] select-none"
                style={{ fontSize: 'clamp(52px, 11vw, 160px)' }}>
                <span style={{ color: '#eeedf5' }}>Decode</span>{' '}
                <span className="gradient-text">Content.</span>
              </h1>
              <p className="text-base sm:text-lg leading-7 sm:leading-8 max-w-md mx-auto mt-4"
                style={{ color: '#b0afc8', opacity: 0.85 }}>
                Drop a YouTube and Instagram Reel URL. PRISM extracts transcripts,
                maps engagement, and lets you interrogate both videos with AI.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-2 mt-5 sm:mt-6 animate-fade-up"
              style={{ animationDelay: '0.3s', opacity: 0 }}>
              {[
                { icon: Layers,        label: 'Transcript RAG' },
                { icon: BarChart2,     label: 'Engagement Analytics' },
                { icon: MessageSquare, label: 'Streaming Chat' },
              ].map(({ icon: Icon, label }) => (
                <div key={label} className="liquid-glass rounded-full px-3 py-1.5 flex items-center gap-1.5">
                  <Icon size={11} style={{ color: '#6b6a8a' }} />
                  <span className="text-xs font-mono" style={{ color: '#6b6a8a' }}>{label}</span>
                </div>
              ))}
            </div>

            <div id="analyse" className="w-full max-w-lg mt-8 sm:mt-10 animate-fade-up"
              style={{ animationDelay: '0.4s', opacity: 0 }}>
              <IngestForm onSuccess={handleIngestSuccess} />
            </div>
          </div>

          {/* Bottom hint */}
          <div className="flex-shrink-0 pb-8 sm:pb-12 flex items-center justify-center">
            <div className="flex items-center gap-3">
              <div className="h-px w-16 sm:w-24" style={{ background: 'rgba(255,255,255,0.06)' }} />
              <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: 'rgba(238,237,245,0.2)' }}>
                scroll to explore
              </span>
              <div className="h-px w-16 sm:w-24" style={{ background: 'rgba(255,255,255,0.06)' }} />
            </div>
          </div>
        </div>
      </div>

      {/* About */}
      <section id="about" className="py-16 sm:py-28 px-4 sm:px-8 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 sm:gap-20 items-start">
          <div id="capabilities">
            <div className="liquid-glass rounded-full px-3 py-1 inline-flex items-center gap-2 mb-5 sm:mb-6">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#818cf8' }} />
              <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: '#6b6a8a' }}>
                System Architecture
              </span>
            </div>
            <h2 className="font-display font-semibold text-2xl sm:text-3xl leading-tight mb-5 sm:mb-6"
              style={{ color: '#eeedf5' }}>
              A multi-modal RAG engine built for content intelligence.
            </h2>
            <p className="text-sm leading-relaxed mb-4" style={{ color: '#b0afc8' }}>
              PRISM is a highly performant multi-modal RAG engine that merges real-time video metadata
              parsing with an automated fallback pipeline. When platform APIs block transcript access,
              an isolated subprocess sandbox downloads raw audio and routes it through AssemblyAI's
              speech-to-text pipeline — so ingestion never fails.
            </p>
            <p className="text-sm leading-relaxed" style={{ color: '#b0afc8' }}>
              Retrieved chunks are embedded via Gemini's native embedding API and catalogued in a
              local Qdrant instance for sub-second semantic retrieval. A dual-LLM router —
              Gemini 2.5 Flash primary, Groq Llama fallback — delivers ~15,900 free requests
              per day with circuit-breaker protection.
            </p>
          </div>

          <div>
            <p className="text-[10px] font-mono uppercase tracking-widest mb-4 sm:mb-5" style={{ color: '#6b6a8a' }}>
              Core Dependencies
            </p>
            <div className="space-y-3">
              {TECH_PILLS.map(({ label, color }) => (
                <div key={label} className="liquid-glass rounded-2xl px-4 sm:px-5 py-3 sm:py-4 flex items-center justify-between">
                  <span className="font-display font-medium text-sm" style={{ color: '#eeedf5' }}>{label}</span>
                  <span className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: color, boxShadow: `0 0 10px ${color}70` }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-4 sm:px-8">
        <div className="h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(255,255,255,0.07), transparent)' }} />
      </div>

      {/* FAQ */}
      <section id="faq" className="py-16 sm:py-28 px-4 sm:px-8 max-w-3xl mx-auto">
        <div className="text-center mb-10 sm:mb-14">
          <div className="liquid-glass rounded-full px-3 py-1 inline-flex items-center gap-2 mb-5 sm:mb-6">
            <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: '#6b6a8a' }}>
              Technical FAQ
            </span>
          </div>
          <h2 className="font-display font-semibold text-2xl sm:text-3xl" style={{ color: '#eeedf5' }}>
            Built for engineers who ask hard questions.
          </h2>
        </div>
        <FaqAccordion />
      </section>

      {/* Footer */}
      <footer className="py-8 sm:py-10 px-4 sm:px-8 text-center"
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center justify-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-md flex items-center justify-center liquid-glass">
            <BarChart2 size={11} style={{ color: '#eeedf5' }} strokeWidth={2.5} />
          </div>
          <span className="font-display font-semibold text-sm" style={{ color: '#eeedf5' }}>PRISM</span>
        </div>
        <p className="text-xs font-mono" style={{ color: '#6b6a8a' }}>
          RAG-powered content intelligence · Gemini · Groq · Qdrant · AssemblyAI
        </p>
      </footer>
    </div>
  )
}

// ── Skeleton components ───────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="liquid-glass rounded-2xl overflow-hidden p-6"
      style={{ background: 'rgba(255,255,255,0.02)' }}>
      <div className="flex items-center justify-between mb-5">
        <Shimmer width="60px" height="10px" />
        <Shimmer width="70px" height="20px" rounded />
      </div>
      <Shimmer width="90%" height="16px" className="mb-2" />
      <Shimmer width="60%" height="16px" className="mb-6" />
      <div className="rounded-2xl p-4 mb-5" style={{ background: 'rgba(129,140,248,0.05)', border: '1px solid rgba(129,140,248,0.1)' }}>
        <Shimmer width="120px" height="10px" className="mb-3" />
        <Shimmer width="80px" height="36px" />
      </div>
      <div className="grid grid-cols-3 gap-2.5 mb-5">
        {[0,1,2].map(i => <Shimmer key={i} height="64px" rounded />)}
      </div>
      <div className="flex gap-4">
        <Shimmer width="60px" height="10px" />
        <Shimmer width="80px" height="10px" />
        <Shimmer width="60px" height="10px" />
      </div>
    </div>
  )
}

function SkeletonChat() {
  return (
    <div className="liquid-glass rounded-2xl overflow-hidden flex flex-col h-full min-h-[500px]"
      style={{ background: 'rgba(255,255,255,0.02)' }}>
      <div className="px-6 py-4 flex items-center justify-between flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(129,140,248,0.3)' }} />
          <Shimmer width="80px" height="12px" />
        </div>
        <Shimmer width="60px" height="20px" rounded />
      </div>
      <div className="p-4 space-y-2 flex-shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <Shimmer width="70px" height="10px" className="mb-3" />
        {[0,1,2,3].map(i => <Shimmer key={i} height="36px" rounded />)}
      </div>
      <div className="flex-1 p-5 flex items-center justify-center">
        <div className="w-10 h-10 rounded-2xl liquid-glass flex items-center justify-center" style={{ opacity: 0.3 }}>
          <BarChart2 size={18} style={{ color: '#818cf8' }} />
        </div>
      </div>
      <div className="px-5 pb-5 pt-3 flex-shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <Shimmer height="52px" rounded />
      </div>
    </div>
  )
}

function Shimmer({ width, height, rounded, className }: {
  width?: string; height: string; rounded?: boolean; className?: string
}) {
  return (
    <div
      className={className}
      style={{
        width: width || '100%',
        height,
        borderRadius: rounded ? '12px' : '6px',
        background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.6s infinite',
      }}
    />
  )
}
