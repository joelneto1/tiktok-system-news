import { useEffect, useRef, useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface LogEntry {
  timestamp: string
  level: 'SUCCESS' | 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
  message: string
}

interface TerminalViewerProps {
  logs: LogEntry[]
  loading?: boolean
  title?: string
}

const LEVEL_COLORS: Record<LogEntry['level'], string> = {
  SUCCESS: 'text-green-400',
  INFO: 'text-slate-300',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  DEBUG: 'text-slate-500',
}

const LEVEL_BADGE_COLORS: Record<LogEntry['level'], string> = {
  SUCCESS: 'text-green-400',
  INFO: 'text-cyan-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  DEBUG: 'text-slate-600',
}

export default function TerminalViewer({
  logs,
  loading = false,
  title = 'system-terminal > /logs',
}: TerminalViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  function handleCopy() {
    const text = logs
      .map((l) => `[${l.timestamp}] [${l.level}] ${l.message}`)
      .join('\n')
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="rounded-xl overflow-hidden border border-[#1e293b] shadow-2xl shadow-black/40">
      {/* Terminal header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#0d1117] border-b border-[#1e293b]">
        <div className="flex items-center gap-3">
          {/* Traffic lights */}
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs font-mono text-slate-500">{title}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-[#1a2235] transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-green-400" />
              <span className="text-green-400">COPIADO</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              COPIAR
            </>
          )}
        </button>
      </div>

      {/* Terminal body */}
      <div
        ref={scrollRef}
        className="bg-[#010409] p-4 overflow-y-auto font-mono text-sm leading-6"
        style={{ maxHeight: '560px', minHeight: '400px' }}
      >
        {loading ? (
          <div className="flex items-center gap-2 text-slate-500">
            <span className="animate-pulse">_</span>
            <span>Carregando logs...</span>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-slate-600">
            Nenhum log encontrado. Aguardando eventos...
          </div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="flex gap-0 hover:bg-[#0d1117]/60 px-1 -mx-1 rounded">
              <span className="text-slate-600 select-none shrink-0">
                [{log.timestamp}]
              </span>
              <span className={cn('mx-1 shrink-0', LEVEL_BADGE_COLORS[log.level])}>
                [{log.level.padEnd(7)}]
              </span>
              <span className={cn(LEVEL_COLORS[log.level])}>
                {log.message}
              </span>
            </div>
          ))
        )}
        {!loading && logs.length > 0 && (
          <div className="flex items-center gap-1 mt-1 text-slate-600">
            <span className="animate-pulse">_</span>
          </div>
        )}
      </div>
    </div>
  )
}
