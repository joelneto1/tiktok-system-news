import { useState, useEffect } from 'react'
import { Play, Clock, Globe, Tag, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { listVideos, type Video as ApiVideo } from '@/api/videos'

interface Video {
  id: string
  topic: string
  model: string
  language: string
  status: 'completed' | 'processing' | 'failed'
  date: string
  duration: string
  thumbnail?: string
}

const STATUS_STYLES: Record<Video['status'], { bg: string; text: string; label: string }> = {
  completed: { bg: 'bg-green-500/10 border-green-500/20', text: 'text-green-400', label: 'Concluido' },
  processing: { bg: 'bg-yellow-500/10 border-yellow-500/20', text: 'text-yellow-400', label: 'Processando' },
  failed: { bg: 'bg-red-500/10 border-red-500/20', text: 'text-red-400', label: 'Falhou' },
}

function mapApiVideo(v: ApiVideo): Video {
  const statusLower = v.status.toLowerCase() as Video['status']
  const validStatus = ['completed', 'processing', 'failed'].includes(statusLower)
    ? statusLower
    : 'processing'

  const durationStr = v.duration
    ? `${Math.floor(v.duration / 60)}:${String(Math.floor(v.duration % 60)).padStart(2, '0')}`
    : '--:--'

  return {
    id: v.id,
    topic: v.topic,
    model: v.model_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    language: v.language,
    status: validStatus,
    date: new Date(v.created_at).toLocaleString('pt-BR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }),
    duration: durationStr,
  }
}

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const resp = await listVideos(1, 50)
        setVideos(resp.videos.map(mapApiVideo))
      } catch {
        // API not available — show empty state
        setVideos([])
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          <span className="text-text-primary">Videos </span>
          <span className="text-cyan-400">Gerados</span>
        </h2>
        <p className="text-text-secondary text-sm mt-1">
          Todos os videos gerados pelo pipeline.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
          <span className="ml-2 text-text-secondary">Carregando...</span>
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20 text-text-secondary">
          Nenhum video encontrado. Inicie o pipeline para gerar videos.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {videos.map((video) => {
            const status = STATUS_STYLES[video.status]
            return (
              <div
                key={video.id}
                className="bg-surface border border-border rounded-xl overflow-hidden hover:border-accent/30 transition-colors cursor-pointer group"
              >
                {/* Thumbnail */}
                <div className="relative aspect-[9/16] max-h-[220px] bg-black flex items-center justify-center overflow-hidden">
                  <div className="flex flex-col items-center gap-2 text-slate-600">
                    <Play className="w-10 h-10" />
                    <span className="text-xs font-mono">{video.duration}</span>
                  </div>
                  {video.status === 'completed' && (
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <div className="w-12 h-12 rounded-full bg-cyan-500/80 flex items-center justify-center">
                        <Play className="w-5 h-5 text-white ml-0.5" />
                      </div>
                    </div>
                  )}
                  {video.status === 'processing' && (
                    <div className="absolute bottom-0 left-0 right-0 h-1 bg-surface">
                      <div className="h-full bg-yellow-400 animate-pulse" style={{ width: '60%' }} />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-3.5 space-y-2.5">
                  <p className="text-sm text-text-primary font-medium leading-snug line-clamp-2">
                    {video.topic}
                  </p>

                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={cn(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border',
                      status.bg, status.text,
                    )}>
                      {status.label}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[10px] text-text-secondary">
                      <Tag className="w-2.5 h-2.5" />
                      {video.model}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[10px] text-text-secondary">
                    <span className="flex items-center gap-1">
                      <Globe className="w-2.5 h-2.5" />
                      {video.language}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      {video.date}
                    </span>
                  </div>

                  <p className="text-[10px] font-mono text-text-secondary/60">
                    ID: {video.id}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
