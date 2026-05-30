'use client'
import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Zap, Bot } from 'lucide-react'
import { ChatMessage } from '@/types'
import { streamChat } from '@/lib/api'
import SourceBadge from './SourceBadge'
import clsx from 'clsx'

interface Props {
  sessionId: string
}

const SUGGESTED = [
  'Why did Video A get more engagement than Video B?',
  'Compare the hooks in the first 5 seconds.',
  "What's the engagement rate of each video?",
  'Suggest improvements for B based on what worked in A.',
]

export default function ChatPanel({ sessionId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [modelUsed, setModelUsed] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(text: string) {
    if (!text.trim() || loading) return

    const userMsg: ChatMessage = { role: 'user', content: text.trim() }
    const assistantMsg: ChatMessage = { role: 'assistant', content: '', streaming: true }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setInput('')
    setLoading(true)
    setModelUsed(null)

    const history = messages.map(m => ({ role: m.role, content: m.content }))

    try {
      let sources = undefined
      let fullContent = ''

      for await (const event of streamChat(sessionId, text.trim(), history)) {
        if (event.type === 'sources') {
          sources = event.data
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], sources }
            return next
          })
        } else if (event.type === 'token' && event.content) {
          fullContent += event.content
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: fullContent,
              streaming: true,
            }
            return next
          })
        } else if (event.type === 'done') {
          setModelUsed(event.model ?? null)
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], streaming: false, model_used: event.model }
            return next
          })
        } else if (event.type === 'error') {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: `Error: ${event.content}`,
              streaming: false,
            }
            return next
          })
        }
      }
    } catch (e: any) {
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: `Failed to get response: ${e.message}`,
          streaming: false,
        }
        return next
      })
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  return (
    <div className="flex flex-col h-full bg-panel rounded-2xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span className="font-display font-700 text-sm text-text tracking-wide">PRISM Chat</span>
        </div>
        {modelUsed && (
          <div className="flex items-center gap-1.5 text-xs font-mono text-ghost">
            <Zap size={10} className={modelUsed === 'gemini' ? 'text-sky' : 'text-signal'} />
            <span>{modelUsed === 'gemini' ? 'Gemini 1.5 Flash' : 'Groq / Llama 3.1'}</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {messages.length === 0 && (
          <div className="space-y-3 animate-fade-up">
            <p className="text-xs font-mono text-ghost text-center mb-4">
              Ask anything about the two videos
            </p>
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="w-full text-left text-xs font-mono text-ghost hover:text-accent border border-border hover:border-accent/40 rounded-xl px-4 py-3 transition-all duration-200 bg-ink hover:bg-accent/5"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={clsx(
              'animate-fade-up',
              msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'
            )}
          >
            <div className={clsx(
              'max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
              msg.role === 'user'
                ? 'bg-accent text-ink font-600 font-display'
                : 'bg-ink border border-border text-text'
            )}>
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-1.5 mb-2">
                  <Bot size={11} className="text-ghost" />
                  <span className="text-xs font-mono text-ghost">PRISM</span>
                  {msg.model_used && (
                    <span className={`text-xs font-mono ml-1 ${
                      msg.model_used === 'gemini' ? 'text-sky' : 'text-signal'
                    }`}>
                      via {msg.model_used}
                    </span>
                  )}
                </div>
              )}

              <p className={clsx(
                'whitespace-pre-wrap',
                msg.streaming && msg.content && 'cursor-blink'
              )}>
                {msg.content || (msg.streaming && !msg.content
                  ? <span className="flex gap-1 items-center py-1">
                      {[0,1,2].map(d => (
                        <span key={d} className="w-1.5 h-1.5 rounded-full bg-ghost animate-pulse-dot"
                          style={{ animationDelay: `${d * 0.16}s` }} />
                      ))}
                    </span>
                  : null
                )}
              </p>

              {msg.sources && <SourceBadge sources={msg.sources} />}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2 border-t border-border">
        <div className="flex items-end gap-2 bg-ink border border-border rounded-xl px-4 py-3 focus-within:border-accent/50 transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about the videos…"
            rows={1}
            disabled={loading}
            className="flex-1 bg-transparent text-sm text-text placeholder-ghost resize-none outline-none font-body leading-relaxed max-h-32 overflow-y-auto"
            style={{ fieldSizing: 'content' } as any}
          />
          <button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            className="flex-shrink-0 w-8 h-8 rounded-lg bg-accent text-ink flex items-center justify-center disabled:opacity-30 hover:bg-accent-dim transition-colors"
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-center text-xs font-mono text-ghost/40 mt-2">
          ↵ send · shift+↵ newline
        </p>
      </div>
    </div>
  )
}
