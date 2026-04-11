import { useState, useRef, useEffect } from 'react'
import { Zap, Upload, Trash2, Play, Pause, CheckCircle2, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { uploadSfx, listSfx, deleteSfx as deleteSfxApi, getSfxDownloadUrl } from '@/api/sfx'

export interface SfxFile {
  id: string
  name: string
  sfxType: string
  url: string
  size: number
  duration?: number
}

interface SfxUploaderProps {
  className?: string
}

const SFX_TYPES = [
  { key: 'whoosh', label: 'Whoosh', description: 'Transicao rapida' },
  { key: 'impact', label: 'Impact', description: 'Dado chocante' },
  { key: 'ding', label: 'Ding', description: 'Informacao importante' },
  { key: 'tension_rise', label: 'Tension Rise', description: 'Construcao de suspense' },
  { key: 'news_flash', label: 'News Flash', description: 'Alerta de noticia' },
] as const

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function showToast(message: string, type: 'success' | 'error' = 'success') {
  const existing = document.getElementById('sfx-toast')
  if (existing) existing.remove()

  const div = document.createElement('div')
  div.id = 'sfx-toast'
  div.style.cssText = 'position:fixed;top:5rem;right:1.5rem;z-index:100;padding:0.875rem 1.25rem;border-radius:0.75rem;display:flex;align-items:center;gap:0.75rem;font-size:0.875rem;font-weight:500;backdrop-filter:blur(12px);border:1px solid;animation:sfxSlideIn 0.3s ease-out;'
  div.style.cssText += type === 'success'
    ? 'background:rgba(34,197,94,0.2);border-color:rgba(34,197,94,0.4);color:rgb(134,239,172);'
    : 'background:rgba(239,68,68,0.2);border-color:rgba(239,68,68,0.4);color:rgb(252,165,165);'
  div.innerHTML = `<span>${type === 'success' ? '\u2713' : '\u2715'}</span><span>${message}</span>`
  document.body.appendChild(div)
  setTimeout(() => div.remove(), 4000)
}

function SfxSlot({ label, description, file, onUpload, onDelete }: {
  label: string
  description: string
  file: SfxFile | undefined
  onUpload: (file: File) => void
  onDelete: () => void
}) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  function togglePlay() {
    if (!file) return
    if (!audioRef.current) {
      audioRef.current = new Audio(file.url)
      audioRef.current.onended = () => setIsPlaying(false)
    }
    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  function handleFileSelect(files: FileList | null) {
    if (!files || files.length === 0) return
    const f = files[0]
    if (f.type.startsWith('audio/') || /\.(mp3|wav|ogg|m4a|aac|flac)$/i.test(f.name)) {
      onUpload(f)
    }
  }

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  // Reset audio element when file changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
      setIsPlaying(false)
    }
  }, [file?.id])

  return (
    <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-background border border-border hover:border-border/80 transition-colors group">
      {/* Status indicator */}
      <div className="shrink-0">
        {file ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
        ) : (
          <div className="w-3.5 h-3.5 rounded-full border-2 border-text-secondary/30" />
        )}
      </div>

      {/* Type info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary font-medium leading-tight">{label}</p>
        <p className="text-[10px] text-text-secondary/60 leading-tight">{description}</p>
        {file && (
          <div className="flex items-center gap-2 text-[10px] text-text-secondary/50 mt-0.5">
            <span>{file.name}</span>
            <span>{formatSize(file.size)}</span>
            {file.duration != null && <span>{formatDuration(file.duration)}</span>}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {file ? (
          <>
            <button onClick={togglePlay}
              className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center transition-colors',
                isPlaying ? 'bg-amber-500/20 text-amber-400' : 'bg-surface-hover text-text-secondary hover:text-amber-400'
              )}>
              {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
            </button>
            <button onClick={() => setDeleteConfirm(true)}
              className="p-1.5 rounded text-text-secondary/60 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Excluir">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </>
        ) : (
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFileSelect(e.dataTransfer.files) }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md cursor-pointer transition-all text-xs',
              isDragging
                ? 'border border-amber-400 bg-amber-500/10 text-amber-400'
                : 'border border-dashed border-border/60 text-text-secondary/50 hover:border-text-secondary/40 hover:text-text-secondary/70 hover:bg-surface-hover/50'
            )}>
            <Upload className="w-3 h-3" />
            <span>Upload</span>
            <input ref={inputRef} type="file" className="hidden"
              accept="audio/*,.mp3,.wav,.ogg,.m4a,.aac,.flac"
              onChange={(e) => { handleFileSelect(e.target.files); if (e.target) e.target.value = '' }} />
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {deleteConfirm && file && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setDeleteConfirm(false)}>
          <div className="bg-surface border border-border rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-red-500/10">
                <AlertTriangle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">Excluir SFX</h3>
                <p className="text-xs text-text-secondary">Esta acao nao pode ser desfeita</p>
              </div>
            </div>
            <p className="text-sm text-text-secondary mb-5">
              Tem certeza que deseja excluir <span className="text-text-primary font-medium">"{file.name}"</span> ({label})?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteConfirm(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-hover border border-border text-text-secondary hover:text-text-primary transition-colors">
                Cancelar
              </button>
              <button onClick={() => { setDeleteConfirm(false); onDelete() }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 hover:bg-red-600 text-white transition-colors">
                Sim, excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function SfxUploader({ className }: SfxUploaderProps) {
  const [sfxFiles, setSfxFiles] = useState<SfxFile[]>([])

  // Load SFX from API on mount
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const resp = await listSfx()
        if (cancelled) return
        const loaded: SfxFile[] = resp.sfx.map((s) => ({
          id: s.id,
          name: s.name,
          sfxType: s.sfx_type,
          url: getSfxDownloadUrl(s.id),
          size: s.file_size ?? 0,
          duration: s.duration ?? undefined,
        }))
        setSfxFiles(loaded)
      } catch { /* API not available */ }
    }
    load()
    return () => { cancelled = true }
  }, [])

  function getFileForType(sfxType: string): SfxFile | undefined {
    return sfxFiles.find((f) => f.sfxType === sfxType)
  }

  async function handleUpload(sfxType: string, label: string, file: File) {
    const blobUrl = URL.createObjectURL(file)
    const tempId = `temp_${crypto.randomUUID()}`

    // 1. Show instantly (optimistic)
    const tempSfx: SfxFile = {
      id: tempId,
      name: file.name,
      sfxType,
      url: blobUrl,
      size: file.size,
    }
    setSfxFiles((prev) => {
      // Remove existing for this type, add new
      const filtered = prev.filter((f) => f.sfxType !== sfxType)
      return [...filtered, tempSfx]
    })

    // 2. Get duration from browser
    try {
      const audio = new Audio(blobUrl)
      await new Promise<void>((resolve) => {
        audio.onloadedmetadata = () => {
          setSfxFiles((prev) =>
            prev.map((f) => f.id === tempId ? { ...f, duration: audio.duration } : f)
          )
          resolve()
        }
        audio.onerror = () => resolve()
        setTimeout(resolve, 3000)
      })
    } catch { /* non-critical */ }

    // 3. Upload to server
    try {
      const resp = await uploadSfx(file, label, sfxType)
      setSfxFiles((prev) =>
        prev.map((f) => {
          if (f.id === tempId) {
            return {
              id: resp.id,
              name: resp.name,
              sfxType: resp.sfx_type,
              url: getSfxDownloadUrl(resp.id),
              size: resp.file_size ?? file.size,
              duration: resp.duration ?? f.duration,
            }
          }
          return f
        })
      )
      showToast(`SFX "${label}" enviado com sucesso!`)
    } catch {
      showToast(`Erro ao enviar SFX "${label}"`, 'error')
    }
  }

  async function handleDelete(sfxType: string) {
    const file = getFileForType(sfxType)
    if (!file) return

    const id = file.id
    const name = file.name

    // Delete on server first
    if (!id.startsWith('temp_')) {
      try {
        await deleteSfxApi(id)
        showToast(`SFX "${name}" excluido com sucesso!`)
      } catch (err) {
        showToast(`Erro ao excluir "${name}"`, 'error')
        console.error('Failed to delete SFX:', err)
        return
      }
    }
    // Then remove from UI
    setSfxFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const uploadedCount = SFX_TYPES.filter((t) => getFileForType(t.key)).length

  return (
    <div className={cn('bg-surface border border-border rounded-xl p-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary">
            Efeitos Sonoros (SFX)
          </h3>
        </div>
        <span className="text-[10px] text-text-secondary/50">
          {uploadedCount}/{SFX_TYPES.length} enviados
        </span>
      </div>

      <div className="space-y-1.5">
        {SFX_TYPES.map((type) => (
          <SfxSlot
            key={type.key}
            label={type.label}
            description={type.description}
            file={getFileForType(type.key)}
            onUpload={(file) => handleUpload(type.key, type.label, file)}
            onDelete={() => handleDelete(type.key)}
          />
        ))}
      </div>

      {uploadedCount === 0 && (
        <p className="text-xs text-text-secondary/40 mt-1.5 text-center">
          Nenhum efeito sonoro adicionado
        </p>
      )}

      <style>{`@keyframes sfxSlideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
    </div>
  )
}
