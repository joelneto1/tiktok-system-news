import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Download,
  RotateCcw,
  FileText,
  Timer,
  Activity,
  Mic,
  Video,
  Search,
  Film,
  BarChart3,
  Layers,
  Upload,
  Play,
  AlertTriangle,
  Settings,
  ScrollText,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  getPipelineStatus,
  retryPipeline,
  type PipelineStatusResponse,
  type StageInfo,
} from '@/api/pipeline'
import { getVideoDownloadUrl, getVideoScript } from '@/api/videos'

// ─── Stage config ───────────────────────────────────────────────

const STAGE_ICONS: Record<string, typeof Zap> = {
  script_generation: FileText,
  tts_synthesis: Mic,
  avatar_generation: Video,
  broll_search: Search,
  broll_download: Film,
  audio_analysis: BarChart3,
  timeline_assembly: Layers,
  video_render: Play,
  upload: Upload,
}

const STAGE_LABELS: Record<string, string> = {
  script_generation: 'Gerar Roteiro',
  tts_synthesis: 'Narração TTS',
  avatar_generation: 'Avatar DreamFace',
  broll_search: 'B-Roll Busca',
  broll_download: 'B-Roll Download',
  audio_analysis: 'Análise de Áudio',
  timeline_assembly: 'Montagem Timeline',
  video_render: 'Render Final',
  upload: 'Upload Storage',
}

const STAGE_SUBS: Record<string, string> = {
  script_generation: 'OpenRouter API',
  tts_synthesis: 'GenAIPro TTS',
  avatar_generation: 'DreamFace + Chromakey',
  broll_search: 'Grok Imagine',
  broll_download: 'CDN download',
  audio_analysis: 'Whisper + Scene Director',
  timeline_assembly: 'Remotion composição',
  video_render: 'Remotion render MP4',
  upload: 'MinIO storage',
}

// ─── Helpers ────────────────────────────────────────────────────

function formatTimer(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

type JobStatus = 'completed' | 'processing' | 'queued' | 'failed'

const STATUS_LABEL: Record<JobStatus, string> = {
  completed: 'COMPLETED',
  processing: 'RUNNING',
  queued: 'QUEUED',
  failed: 'FAILED',
}

const STATUS_COLOR: Record<JobStatus, string> = {
  completed: 'text-success',
  processing: 'text-accent',
  queued: 'text-text-secondary',
  failed: 'text-error',
}

const BADGE_COLOR: Record<JobStatus, string> = {
  completed: 'bg-success/10 border-success/20 text-success',
  processing: 'bg-accent/10 border-accent/20 text-accent',
  queued: 'bg-surface border-border text-text-secondary',
  failed: 'bg-error/10 border-error/20 text-error',
}

// ─── Tab type ───────────────────────────────────────────────────

type TabId = 'pipeline' | 'config' | 'log'

// ─── Main Component ─────────────────────────────────────────────

export default function PipelineDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const [data, setData] = useState<PipelineStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [activeTab, setActiveTab] = useState<TabId>('pipeline')
  const [script, setScript] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Fetch ──
  const fetchStatus = useCallback(async () => {
    if (!jobId) return
    try {
      const resp = await getPipelineStatus(jobId)
      setData(resp)
      setError(null)
    } catch {
      setError('Erro ao carregar status do pipeline')
    }
  }, [jobId])

  useEffect(() => {
    fetchStatus().finally(() => setIsLoading(false))
  }, [fetchStatus])

  // ── Auto-refresh (3s when processing) ──
  useEffect(() => {
    const isActive = data?.video.status === 'processing'
    if (isActive && !intervalRef.current) {
      intervalRef.current = setInterval(fetchStatus, 3000)
    } else if (!isActive && intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [data?.video.status, fetchStatus])

  // ── Timer ──
  useEffect(() => {
    const video = data?.video
    if (!video) return

    if (video.status === 'processing' && video.started_at) {
      const startTime = new Date(video.started_at).getTime()
      const tick = () => setElapsed(Math.floor((Date.now() - startTime) / 1000))
      tick()
      timerRef.current = setInterval(tick, 1000)
    } else if (video.started_at && video.completed_at) {
      const start = new Date(video.started_at).getTime()
      const end = new Date(video.completed_at).getTime()
      setElapsed(Math.floor((end - start) / 1000))
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [data?.video])

  // ── Fetch script on tab switch ──
  useEffect(() => {
    if (activeTab === 'config' && jobId && !script) {
      getVideoScript(jobId)
        .then((resp) => setScript(resp.script))
        .catch(() => setScript(null))
    }
  }, [activeTab, jobId, script])

  // ── Handlers ──
  async function handleRetry() {
    if (!jobId) return
    setRetrying(true)
    try {
      await retryPipeline(jobId)
      await fetchStatus()
    } finally {
      setRetrying(false)
    }
  }

  function handleDownload() {
    if (!jobId) return
    window.open(getVideoDownloadUrl(jobId), '_blank')
  }

  // ── Loading / Error ──
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
        <span className="ml-2 text-text-secondary">Carregando...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4">
        <AlertTriangle className="w-8 h-8 text-error" />
        <p className="text-text-secondary">{error ?? 'Não encontrado'}</p>
        <button onClick={() => navigate('/pipeline')} className="text-accent hover:underline text-sm">
          Voltar
        </button>
      </div>
    )
  }

  const { video, stages } = data
  const status = video.status as JobStatus
  const progress = video.progress_percent

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* ── Back ── */}
        <button
          onClick={() => navigate('/pipeline')}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Voltar
        </button>

        {/* ══════════════════════════════════════════════════════════
            TOP CARD: Job ID + Badge + Timer + Info Cards + Progress
           ══════════════════════════════════════════════════════════ */}
        <div className="rounded-xl bg-surface border border-border p-6 space-y-6">
          {/* Row 1: Job ID + badge + timer */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold text-text-primary">
                Job {video.id.slice(0, 8)}
              </h1>
              <span
                className={cn(
                  'text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border',
                  BADGE_COLOR[status],
                )}
              >
                {STATUS_LABEL[status]}
              </span>
            </div>
            {/* Timer */}
            {(status === 'processing' || status === 'completed' || status === 'failed') &&
              elapsed > 0 && (
                <div className="text-right">
                  <p className="text-[10px] uppercase tracking-wider text-text-secondary/50 font-semibold">
                    Tempo decorrido
                  </p>
                  <p
                    className={cn(
                      'text-3xl font-bold tabular-nums tracking-tight mt-0.5',
                      status === 'processing' ? 'text-accent' : 'text-text-primary',
                    )}
                  >
                    {formatTimer(elapsed)}
                  </p>
                </div>
              )}
          </div>

          {/* Row 2: 3 info cards */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-background border border-border p-4">
              <p className="text-[10px] uppercase tracking-wider text-text-secondary/50 font-semibold">
                Etapas
              </p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {video.total_stages}
              </p>
              <p className="text-[10px] text-text-secondary/40 mt-0.5">
                {video.model_type === 'news_tradicional' ? 'Tradicional' : video.model_type}
              </p>
            </div>
            <div className="rounded-lg bg-background border border-border p-4">
              <p className="text-[10px] uppercase tracking-wider text-text-secondary/50 font-semibold">
                Passos concluídos
              </p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {video.completed_stages}/{video.total_stages}
              </p>
              <p className="text-[10px] text-text-secondary/40 mt-0.5">
                {video.language}
              </p>
            </div>
            <div className="rounded-lg bg-background border border-border p-4">
              <p className="text-[10px] uppercase tracking-wider text-text-secondary/50 font-semibold">
                Status
              </p>
              <p className={cn('text-2xl font-bold mt-1', STATUS_COLOR[status])}>
                {STATUS_LABEL[status]}
              </p>
              {video.attempts > 1 && (
                <p className="text-[10px] text-text-secondary/40 mt-0.5">
                  Tentativa {video.attempts}
                </p>
              )}
            </div>
          </div>

          {/* Row 3: Progress bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary/60 font-medium">
                Progresso das etapas
              </span>
              <span className="text-xs text-text-secondary/60 tabular-nums">
                {video.completed_stages}/{video.total_stages} concluídas
              </span>
            </div>
            <div className="h-2 bg-background rounded-full overflow-hidden border border-border">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-700 ease-out',
                  status === 'failed'
                    ? 'bg-error'
                    : status === 'completed'
                      ? 'bg-success'
                      : 'bg-accent',
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Error message */}
          {video.error_message && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-error/5 border border-error/10">
              <XCircle className="w-4 h-4 text-error shrink-0 mt-0.5" />
              <p className="text-xs text-error/80 leading-relaxed">{video.error_message}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2">
            {status === 'failed' && (
              <button
                onClick={handleRetry}
                disabled={retrying}
                className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-warning/10 border border-warning/20 text-warning hover:bg-warning/20 transition-colors disabled:opacity-50"
              >
                <RotateCcw className={cn('w-3.5 h-3.5', retrying && 'animate-spin')} />
                Retomar Pipeline
              </button>
            )}
            {status === 'completed' && (
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-success/10 border border-success/20 text-success hover:bg-success/20 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Download Video
              </button>
            )}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════
            TABS: Pipeline | Configurações | Log
           ══════════════════════════════════════════════════════════ */}
        <div className="flex items-center gap-1">
          {([
            { id: 'pipeline' as TabId, label: 'Pipeline', icon: Activity },
            { id: 'config' as TabId, label: 'Configurações', icon: Settings },
            { id: 'log' as TabId, label: 'Log', icon: ScrollText },
          ]).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                'flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider px-4 py-2 rounded-full border transition-colors',
                activeTab === id
                  ? 'bg-accent/10 border-accent/30 text-accent'
                  : 'bg-transparent border-transparent text-text-secondary/50 hover:text-text-secondary hover:bg-surface-hover',
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* ══════════════════════════════════════════════════════════
            TAB: Pipeline — Stage list
           ══════════════════════════════════════════════════════════ */}
        {activeTab === 'pipeline' && (
          <div className="space-y-2">
            {stages.map((stage, idx) => {
              const Icon = STAGE_ICONS[stage.name] ?? Zap
              const label = STAGE_LABELS[stage.name] ?? stage.name
              const sub = STAGE_SUBS[stage.name] ?? stage.description
              const isDone = stage.status === 'completed'
              const isActive = stage.status === 'in_progress'
              const isFailed = stage.status === 'failed'
              const isPending = stage.status === 'pending'

              const borderColor = isDone
                ? 'border-l-success'
                : isActive
                  ? 'border-l-accent'
                  : isFailed
                    ? 'border-l-error'
                    : 'border-l-border'

              return (
                <div
                  key={stage.name}
                  className={cn(
                    'flex items-center gap-4 px-5 py-4 rounded-xl bg-surface border border-border border-l-[3px] transition-all',
                    borderColor,
                    isActive && 'bg-accent/5 border-accent/20',
                    isFailed && 'bg-error/5 border-error/20',
                  )}
                >
                  {/* Icon */}
                  <div
                    className={cn(
                      'w-9 h-9 rounded-lg flex items-center justify-center shrink-0',
                      isDone
                        ? 'bg-success/10'
                        : isActive
                          ? 'bg-accent/10'
                          : isFailed
                            ? 'bg-error/10'
                            : 'bg-background',
                    )}
                  >
                    <Icon
                      className={cn(
                        'w-4 h-4',
                        isDone
                          ? 'text-success'
                          : isActive
                            ? 'text-accent'
                            : isFailed
                              ? 'text-error'
                              : 'text-text-secondary/20',
                      )}
                    />
                  </div>

                  {/* Text */}
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        'text-sm font-semibold',
                        isPending ? 'text-text-secondary/30' : 'text-text-primary',
                      )}
                    >
                      Etapa {idx + 1} — {label}
                    </p>
                    <p
                      className={cn(
                        'text-[11px] mt-0.5',
                        isPending ? 'text-text-secondary/20' : 'text-text-secondary/50',
                      )}
                    >
                      {sub}
                    </p>
                  </div>

                  {/* Status badge */}
                  {isDone && (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-success uppercase tracking-wider">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Done
                    </span>
                  )}
                  {isActive && (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-accent uppercase tracking-wider">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Running
                    </span>
                  )}
                  {isFailed && (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-error uppercase tracking-wider">
                      <XCircle className="w-3.5 h-3.5" />
                      Failed
                    </span>
                  )}
                </div>
              )
            })}

            {/* Final step: Concluído */}
            <div
              className={cn(
                'flex items-center gap-4 px-5 py-4 rounded-xl bg-surface border border-border border-l-[3px] transition-all',
                status === 'completed' ? 'border-l-success bg-success/5' : 'border-l-border',
              )}
            >
              <div
                className={cn(
                  'w-9 h-9 rounded-lg flex items-center justify-center shrink-0',
                  status === 'completed' ? 'bg-success/10' : 'bg-background',
                )}
              >
                <CheckCircle2
                  className={cn(
                    'w-4 h-4',
                    status === 'completed' ? 'text-success' : 'text-text-secondary/20',
                  )}
                />
              </div>
              <div className="flex-1">
                <p
                  className={cn(
                    'text-sm font-semibold',
                    status === 'completed' ? 'text-text-primary' : 'text-text-secondary/30',
                  )}
                >
                  Concluído — Video Finalizado!
                </p>
                <p
                  className={cn(
                    'text-[11px] mt-0.5',
                    status === 'completed' ? 'text-text-secondary/50' : 'text-text-secondary/20',
                  )}
                >
                  Pipeline completo. Video disponível para download.
                </p>
              </div>
              {status === 'completed' && (
                <span className="flex items-center gap-1 text-[10px] font-bold text-success uppercase tracking-wider">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Done
                </span>
              )}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════
            TAB: Configurações
           ══════════════════════════════════════════════════════════ */}
        {activeTab === 'config' && (
          <div className="space-y-4">
            {/* Info grid */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Tópico', value: video.topic },
                { label: 'Modelo', value: video.model_type === 'news_tradicional' ? 'Tradicional' : video.model_type },
                { label: 'Idioma', value: video.language },
                { label: 'Criado em', value: formatDate(video.created_at) },
              ].map((item) => (
                <div key={item.label} className="rounded-xl bg-surface border border-border p-4">
                  <p className="text-[10px] uppercase tracking-wider text-text-secondary/50 font-semibold">
                    {item.label}
                  </p>
                  <p className="text-sm font-medium text-text-primary mt-1.5">{item.value}</p>
                </div>
              ))}
            </div>

            {/* Script */}
            {(script || video.script) && (
              <div className="rounded-xl bg-surface border border-border overflow-hidden">
                <div className="px-5 py-4 border-b border-border flex items-center gap-2">
                  <FileText className="w-4 h-4 text-accent" />
                  <span className="text-sm font-semibold text-text-primary">Roteiro Gerado</span>
                  <span className="text-[10px] text-text-secondary bg-background border border-border rounded-full px-2 py-0.5 ml-auto tabular-nums">
                    {(script ?? video.script ?? '').length} chars
                  </span>
                </div>
                <div className="p-5">
                  <pre className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap font-sans max-h-72 overflow-y-auto">
                    {script ?? video.script}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════
            TAB: Log
           ══════════════════════════════════════════════════════════ */}
        {activeTab === 'log' && (
          <div className="rounded-xl bg-surface border border-border p-5">
            <div className="flex items-center gap-2 mb-4">
              <ScrollText className="w-4 h-4 text-accent" />
              <span className="text-sm font-semibold text-text-primary">Execution Log</span>
            </div>
            <div className="bg-background rounded-lg border border-border p-4 max-h-96 overflow-y-auto font-mono text-xs space-y-1 text-text-secondary">
              {stages.map((stage) => {
                const time = stage.started_at
                  ? new Date(stage.started_at).toLocaleTimeString('pt-BR')
                  : '--:--:--'
                const label = STAGE_LABELS[stage.name] ?? stage.name
                const color =
                  stage.status === 'completed'
                    ? 'text-success'
                    : stage.status === 'failed'
                      ? 'text-error'
                      : stage.status === 'in_progress'
                        ? 'text-accent'
                        : 'text-text-secondary/30'
                return (
                  <div key={stage.name} className="flex gap-3">
                    <span className="text-text-secondary/40 shrink-0">[{time}]</span>
                    <span className={cn('uppercase text-[10px] font-bold w-16 shrink-0', color)}>
                      {stage.status === 'completed'
                        ? 'OK'
                        : stage.status === 'in_progress'
                          ? 'RUN'
                          : stage.status === 'failed'
                            ? 'FAIL'
                            : 'WAIT'}
                    </span>
                    <span>{label}</span>
                  </div>
                )
              })}
              {video.error_message && (
                <div className="flex gap-3 text-error mt-2 pt-2 border-t border-border">
                  <span className="text-error/40 shrink-0">[ERROR]</span>
                  <span>{video.error_message}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
