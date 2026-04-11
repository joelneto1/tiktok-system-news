import { useState, useMemo, useEffect, useCallback } from 'react'
import { Search, Filter, Loader2 } from 'lucide-react'
import TerminalViewer, { type LogEntry } from '@/components/logs/TerminalViewer'
import { listLogs } from '@/api/logs'

const LEVELS = ['TODOS', 'SUCCESS', 'INFO', 'WARNING', 'ERROR', 'DEBUG'] as const

export default function LogsPage() {
  const [levelFilter, setLevelFilter] = useState<string>('TODOS')
  const [jobIdSearch, setJobIdSearch] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchLogs = useCallback(async () => {
    try {
      const resp = await listLogs({
        page: 1,
        page_size: 200,
        level: levelFilter !== 'TODOS' ? levelFilter : undefined,
        search: jobIdSearch || undefined,
      })
      // Reverse to show oldest first (terminal style: newest at bottom)
      const reversed = [...resp.logs].reverse()
      const mapped: LogEntry[] = reversed.map((l) => {
        // Parse UTC timestamp and convert to local timezone (Brasilia = UTC-3)
        const date = new Date(l.timestamp)
        const timeStr = date.toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
          timeZone: 'America/Sao_Paulo',
        })
        return {
          timestamp: timeStr,
          level: l.level.toUpperCase() as LogEntry['level'],
          message: l.message,
        }
      })
      setLogs(mapped)
    } catch {
      // API not available — show empty state
      setLogs([])
    } finally {
      setIsLoading(false)
    }
  }, [levelFilter, jobIdSearch])

  useEffect(() => {
    setIsLoading(true)
    const timer = setTimeout(() => {
      fetchLogs()
    }, 300) // debounce search

    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      fetchLogs()
    }, 5000)

    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [fetchLogs])

  const filteredLogs = useMemo(() => {
    // Client-side filtering is still useful for instant feedback
    return logs.filter((log) => {
      if (levelFilter !== 'TODOS' && log.level !== levelFilter) return false
      if (jobIdSearch && !log.message.toLowerCase().includes(jobIdSearch.toLowerCase())) return false
      return true
    })
  }, [logs, levelFilter, jobIdSearch])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          <span className="text-text-primary">Execucao </span>
          <span className="text-cyan-400">Logs</span>
        </h2>
        <p className="text-text-secondary text-sm mt-1">
          Eventos detalhados do sistema e erros.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Level dropdown */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-text-secondary" />
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-surface border border-border text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          >
            {LEVELS.map((level) => (
              <option key={level} value={level}>
                {level === 'TODOS' ? 'Todos os niveis' : level}
              </option>
            ))}
          </select>
        </div>

        {/* Job ID search */}
        <div className="relative flex-1 min-w-[200px] max-w-[320px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            placeholder="Buscar por Job ID ou mensagem..."
            value={jobIdSearch}
            onChange={(e) => setJobIdSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-surface border border-border text-text-primary placeholder:text-text-secondary/50 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        {/* Date range */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 rounded-lg bg-surface border border-border text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
          <span className="text-text-secondary text-sm">ate</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 rounded-lg bg-surface border border-border text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        {/* Count badge */}
        <span className="ml-auto text-xs font-mono text-text-secondary bg-surface border border-border px-2.5 py-1 rounded-full">
          {filteredLogs.length} eventos
        </span>
      </div>

      {/* Terminal */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-accent" />
          <span className="ml-2 text-sm text-text-secondary">Carregando...</span>
        </div>
      ) : (
        <TerminalViewer logs={filteredLogs} />
      )}
    </div>
  )
}
