import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RefreshCw,
  FileText,
  Download,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  CircleDot,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { listVideos, getVideoDownloadUrl } from '@/api/videos'

type JobStatus = 'COMPLETED' | 'PROCESSING' | 'QUEUED' | 'FAILED'

interface Job {
  id: string
  topic: string
  reference: string | null
  model: string
  resolution: string
  status: JobStatus
  createdAt: string
}

const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; color: string; icon: typeof CheckCircle2; pulse?: boolean }
> = {
  COMPLETED: {
    label: 'Concluido',
    color: 'text-success bg-success/10 border-success/20',
    icon: CheckCircle2,
  },
  PROCESSING: {
    label: 'Processando',
    color: 'text-accent bg-accent/10 border-accent/20',
    icon: Loader2,
    pulse: true,
  },
  QUEUED: {
    label: 'Na Fila',
    color: 'text-text-secondary bg-surface border-border',
    icon: Clock,
  },
  FAILED: {
    label: 'Falhou',
    color: 'text-error bg-error/10 border-error/20',
    icon: XCircle,
  },
}

const MODEL_COLORS: Record<string, string> = {
  news_tradicional: 'text-accent bg-accent/10 border-accent/20',
  news_jornalistico: 'text-warning bg-warning/10 border-warning/20',
  news_ice: 'text-error bg-error/10 border-error/20',
}

function StatusBadge({ status }: { status: JobStatus }) {
  const config = STATUS_CONFIG[status]
  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border',
        config.color,
      )}
    >
      <Icon className={cn('w-3 h-3', config.pulse && 'animate-spin')} />
      {config.label}
    </span>
  )
}

function ModelBadge({ model }: { model: string }) {
  const label =
    model === 'news_tradicional'
      ? 'Tradicional'
      : model === 'news_jornalistico'
        ? 'Jornalistico'
        : 'ICE'
  const color = MODEL_COLORS[model] ?? 'text-text-secondary bg-surface border-border'

  return (
    <span
      className={cn(
        'inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full border',
        color,
      )}
    >
      {label}
    </span>
  )
}

interface JobHistoryTableProps {
  className?: string
}

export default function JobHistoryTable({ className }: JobHistoryTableProps) {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState<Job[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const fetchJobs = useCallback(async () => {
    try {
      const resp = await listVideos(1, 20)
      const mapped: Job[] = resp.videos.map((v) => ({
        id: v.id,
        topic: v.topic,
        reference: null,
        model: v.model_type,
        resolution: '1080x1920',
        status: v.status.toUpperCase() as JobStatus,
        createdAt: v.created_at,
      }))
      setJobs(mapped)
    } catch {
      // API not available — show empty state
      setJobs([])
    }
  }, [])

  useEffect(() => {
    fetchJobs().finally(() => setIsLoading(false))
  }, [fetchJobs])

  async function handleRefresh() {
    setIsRefreshing(true)
    await fetchJobs()
    setIsRefreshing(false)
  }

  function handleDownload(jobId: string) {
    window.open(getVideoDownloadUrl(jobId), '_blank')
  }

  function formatDate(iso: string) {
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className={cn('rounded-xl bg-surface border border-border overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-text-primary">Historico de Jobs</h2>
          <span className="text-[10px] font-bold text-text-secondary bg-background border border-border rounded-full px-2 py-0.5 tabular-nums">
            {jobs.length}
          </span>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className={cn(
            'flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors',
            'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
            isRefreshing && 'opacity-50 cursor-not-allowed',
          )}
        >
          <RefreshCw className={cn('w-3.5 h-3.5', isRefreshing && 'animate-spin')} />
          Atualizar
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-accent" />
          <span className="ml-2 text-sm text-text-secondary">Carregando...</span>
        </div>
      )}

      {/* Table */}
      {!isLoading && jobs.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {['ID', 'Topico', 'Referencia', 'Config', 'Status', 'Data', 'Acao'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary/70 text-left"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  onClick={() => navigate(`/pipeline/${job.id}`)}
                  className="border-b border-border/50 hover:bg-surface-hover cursor-pointer transition-colors"
                >
                  {/* ID */}
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono text-accent/80">
                      #{job.id.slice(0, 6)}
                    </code>
                  </td>

                  {/* Topic */}
                  <td className="px-4 py-3 max-w-[240px]">
                    <span className="text-sm text-text-primary truncate block">
                      {job.topic}
                    </span>
                  </td>

                  {/* Reference */}
                  <td className="px-4 py-3">
                    <span className="text-xs text-text-secondary">
                      {job.reference ?? '--'}
                    </span>
                  </td>

                  {/* Config */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <ModelBadge model={job.model} />
                      <span className="text-[10px] font-mono text-text-secondary/60 bg-background border border-border rounded px-1.5 py-0.5">
                        {job.resolution}
                      </span>
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3">
                    <StatusBadge status={job.status} />
                  </td>

                  {/* Date */}
                  <td className="px-4 py-3">
                    <span className="text-xs text-text-secondary tabular-nums">
                      {formatDate(job.createdAt)}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1.5 rounded-md bg-background border border-border text-text-secondary hover:text-text-primary hover:border-text-secondary/30 transition-colors"
                        title="Ver script"
                      >
                        <FileText className="w-3 h-3" />
                        Script
                      </button>
                      {job.status === 'COMPLETED' && (
                        <button
                          type="button"
                          onClick={() => handleDownload(job.id)}
                          className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1.5 rounded-md bg-error/10 border border-error/20 text-error hover:bg-error/20 transition-colors"
                          title="Download video"
                        >
                          <Download className="w-3 h-3" />
                          Download
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && jobs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-text-secondary/50">
          <CircleDot className="w-8 h-8 mb-2" />
          <span className="text-sm">Nenhum job encontrado</span>
        </div>
      )}
    </div>
  )
}
