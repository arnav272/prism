'use client'
import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react'
import { Send, Square, Bot, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'
import { ChatMessage } from '@/types'
import { streamChat } from '@/lib/api'
import SourceBadge from './SourceBadge'
import clsx from 'clsx'

interface Props { sessionId: string }

const SUGGESTED = [
  'Why did Video A get more engagement than Video B?',
  'Compare the hooks in the first 5 seconds.',
  "What's the engagement rate of each video?",
  'Suggest improvements for B based on what worked in A.',
  'Which creator has more followers?',
  'Summarize Video B transcript in 3 sentences.',
]

const MODEL_CFG: Record<string, { label: string; color: string }> = {
  gemini: { label: 'Gemini 2.5', color: '#818cf8' },
  groq:   { label: 'Groq',       color: '#a855f7' },
}

function ModelPill({ model }: { model: string }) {
  const cfg = MODEL_CFG[model] ?? { label: model, color: '#6b6a8a' }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono tracking-wider uppercase"
      style={{
        color: cfg.color,
        background: `${cfg.color}12`,
        border: `1px solid ${cfg.color}25`,
      }}>
      {cfg.label}
    </span>
  )
}

function MdText({ text }: { text: string }) {
  return (
    <div className="space-y-1.5">
      {text.split('\n').map((line, li) => {
        if (!line.trim()) return <br key={li} />
        const parts = line.split(/(\*\*[^*]+\*\*)/g)
        return (
          <p key={li} className="leading-relaxed" style={{ fontSize: 13 }}>
            {parts.map((part, pi) =>
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={pi} style={{ color: '#eeedf5', fontWeight: 600 }}>{part.slice(2,-2)}</strong>
                : <span key={pi}>{part}</span>
            )}
          </p>
        )
      })}
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy}
      className="flex items-center gap-1 text-[10px] font-mono mt-3 transition-colors"
      style={{ color: copied ? '#818cf8' : 'rgba(107,106,138,0.45)' }}>
      {copied ? <Check size={9} /> : <Copy size={9} />}
      {copied ? 'Copied' : 'Copy response'}
    </button>
  )
}

const TIMEOUT_MS = 15000

export default function ChatPanel({ sessionId }: Props) {
  const [messages, setMessages]       = useState<ChatMessage[]>([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [modelUsed, setModelUsed]     = useState<string | null>(null)
  const [suggestOpen, setSuggestOpen] = useState(true)
  const bottomRef  = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLTextAreaElement>(null)
  const abortRef   = useRef<AbortController | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const askedRef   = useRef<Set<string>>(new Set())

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  function clearTO() { if (timeoutRef.current) clearTimeout(timeoutRef.current) }
  function resetTO(fn: () => void) { clearTO(); timeoutRef.current = setTimeout(fn, TIMEOUT_MS) }

  function cancelStream() {
    abortRef.current?.abort(); clearTO(); setLoading(false)
    setMessages(prev => {
      const next = [...prev]; const last = next[next.length-1]
      if (last?.streaming) next[next.length-1] = { ...last, content: (last.content||'')+(last.content?'\n\n_[Cancelled]_':'_[Cancelled]_'), streaming: false }
      return next
    })
  }

  const send = useCallback(async (text: string) => {
    if (!text.trim() || loading) return
    askedRef.current.add(text)
    setSuggestOpen(false)
    setMessages(prev => [...prev,
      { role: 'user', content: text.trim() },
      { role: 'assistant', content: '', streaming: true },
    ])
    setInput(''); setLoading(true); setModelUsed(null)
    const controller = new AbortController()
    abortRef.current = controller
    const history = messages.map(m => ({ role: m.role, content: m.content }))
    resetTO(() => {
      cancelStream()
      setMessages(prev => { const n=[...prev]; const l=n[n.length-1]; if(l?.streaming) n[n.length-1]={...l,content:l.content||'Timed out. Try again.',streaming:false}; return n })
    })
    try {
      let full = ''
      for await (const event of streamChat(sessionId, text.trim(), history)) {
        if (controller.signal.aborted) break
        if (event.type==='sources') { setMessages(prev=>{const n=[...prev];n[n.length-1]={...n[n.length-1],sources:event.data};return n}) }
        else if (event.type==='token'&&event.content) { resetTO(()=>cancelStream()); full+=event.content; setMessages(prev=>{const n=[...prev];n[n.length-1]={...n[n.length-1],content:full,streaming:true};return n}) }
        else if (event.type==='done') { clearTO(); setModelUsed(event.model??null); setMessages(prev=>{const n=[...prev];n[n.length-1]={...n[n.length-1],streaming:false,model_used:event.model};return n}) }
        else if (event.type==='error') { clearTO(); setMessages(prev=>{const n=[...prev];n[n.length-1]={...n[n.length-1],content:`Error: ${event.content}`,streaming:false};return n}) }
      }
    } catch(e:any) {
      clearTO()
      if (e?.name!=='AbortError') { setMessages(prev=>{const n=[...prev];n[n.length-1]={...n[n.length-1],content:`Failed: ${e.message}`,streaming:false};return n}) }
    } finally { clearTO(); setLoading(false) }
  }, [loading, messages, sessionId])

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key==='Enter'&&!e.shiftKey) { e.preventDefault(); send(input) }
  }

  const unanswered = SUGGESTED.filter(q => !askedRef.current.has(q))

  return (
    <div className="flex flex-col h-full rounded-2xl overflow-hidden liquid-glass"
      style={{ background: 'rgba(255,255,255,0.02)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#818cf8' }} />
          <span className="font-display font-semibold text-sm" style={{ color: '#eeedf5' }}>
            PRISM Chat
          </span>
        </div>
        <div className="flex items-center gap-2">
          {modelUsed && <ModelPill model={modelUsed} />}
          <Bot size={13} style={{ color: '#6b6a8a' }} />
        </div>
      </div>

      {/* Suggested — collapsible */}
      <div className="flex-shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <button
          onClick={() => setSuggestOpen(o => !o)}
          className="w-full flex items-center justify-between px-6 py-3 transition-colors hover:bg-white/[0.02]">
          <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: '#6b6a8a' }}>
            Suggested questions {unanswered.length > 0 && `(${unanswered.length})`}
          </span>
          {suggestOpen
            ? <ChevronUp size={12} style={{ color: '#6b6a8a' }} />
            : <ChevronDown size={12} style={{ color: '#6b6a8a' }} />
          }
        </button>

        {suggestOpen && unanswered.length > 0 && (
          <div className="px-4 pb-4 grid grid-cols-1 gap-1.5">
            {unanswered.slice(0,4).map(q => (
              <button key={q} onClick={() => send(q)} disabled={loading}
                className="w-full text-left text-xs font-mono rounded-xl px-4 py-2.5 transition-all disabled:opacity-30"
                style={{
                  color: 'rgba(238,237,245,0.55)',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.color = '#eeedf5'
                  ;(e.currentTarget as HTMLElement).style.borderColor = 'rgba(129,140,248,0.3)'
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.color = 'rgba(238,237,245,0.55)'
                  ;(e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.06)'
                }}>
                {q}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <div className="w-10 h-10 rounded-2xl liquid-glass flex items-center justify-center">
              <Bot size={18} style={{ color: '#818cf8' }} />
            </div>
            <p className="text-xs font-mono text-center" style={{ color: 'rgba(107,106,138,0.5)' }}>
              Select a suggestion above or type your question
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={clsx('animate-fade-up', msg.role==='user' ? 'flex justify-end' : 'flex justify-start')}>
            <div className="max-w-[88%] rounded-2xl px-5 py-4"
              style={msg.role==='user'
                ? {
                    background: 'rgba(129,140,248,0.08)',
                    border: '1px solid rgba(129,140,248,0.18)',
                    color: '#eeedf5',
                  }
                : {
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.07)',
                    color: '#eeedf5',
                  }
              }>

              {/* User label */}
              {msg.role==='user' && (
                <div className="flex items-center gap-1.5 mb-2">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#818cf8' }} />
                  <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: 'rgba(129,140,248,0.6)' }}>
                    You
                  </span>
                </div>
              )}

              {/* Assistant label */}
              {msg.role==='assistant' && (
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                  <Bot size={11} style={{ color: '#6b6a8a', flexShrink: 0 }} />
                  <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: '#6b6a8a' }}>
                    PRISM
                  </span>
                  {msg.model_used && <ModelPill model={msg.model_used} />}
                </div>
              )}

              {/* Content */}
              {msg.content ? (
                <div className={clsx(msg.streaming && 'cursor-blink')} style={{ color: '#b0afc8' }}>
                  <MdText text={msg.content} />
                </div>
              ) : msg.streaming ? (
                <span className="flex gap-1.5 items-center py-1">
                  {[0,1,2].map(d => (
                    <span key={d} className="w-1.5 h-1.5 rounded-full animate-pulse-dot"
                      style={{ background: '#6b6a8a', animationDelay: `${d*0.16}s` }} />
                  ))}
                </span>
              ) : null}

              {msg.role==='assistant' && !msg.streaming && msg.content && <CopyButton text={msg.content} />}
              {msg.sources && <SourceBadge sources={msg.sources} />}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 pb-5 pt-3 flex-shrink-0"
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-end gap-2 rounded-2xl px-4 py-3.5 transition-colors"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <textarea
            ref={inputRef} value={input} onChange={e=>setInput(e.target.value)}
            onKeyDown={onKeyDown} placeholder="Ask anything about the two videos…"
            rows={1} disabled={loading}
            className="flex-1 bg-transparent text-sm resize-none outline-none leading-relaxed max-h-32 overflow-y-auto font-mono"
            style={{ color: '#eeedf5', fieldSizing: 'content' } as any} />
          {loading ? (
            <button onClick={cancelStream}
              className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-colors"
              style={{ background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.25)', color: '#a855f7' }}>
              <Square size={12} fill="currentColor" />
            </button>
          ) : (
            <button onClick={() => send(input)} disabled={!input.trim()}
              className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all disabled:opacity-30 hover:scale-105"
              style={{ background: 'rgba(129,140,248,0.15)', border: '1px solid rgba(129,140,248,0.3)', color: '#818cf8' }}>
              <Send size={13} />
            </button>
          )}
        </div>
        <p className="text-center text-[10px] font-mono mt-2" style={{ color: 'rgba(107,106,138,0.3)' }}>
          ↵ send · shift+↵ newline · ■ cancel
        </p>
      </div>
    </div>
  )
}
