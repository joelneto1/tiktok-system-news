import { useState, useRef, useEffect } from 'react'
import { Music, Upload, Trash2, Play, Pause, Download, Pencil, Check, X, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { uploadAudio, listAudios, deleteAudio as deleteAudioApi, renameAudio as renameAudioApi, getAudioDownloadUrl } from '@/api/audios'

export interface AudioFile {
  id: string
  name: string
  url: string
  size: number
  duration?: number
  createdAt?: string
}

interface AudioUploaderProps {
  audios: AudioFile[]
  onAudiosChange: React.Dispatch<React.SetStateAction<AudioFile[]>>
  className?: string
}

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

function AudioItem({ audio, onDelete, onRename, onDownload }: {
  audio: AudioFile
  onDelete: () => void
  onRename: (name: string) => void
  onDownload: () => void
}) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isRenaming, setIsRenaming] = useState(false)
  const [newName, setNewName] = useState(audio.name)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  function togglePlay() {
    if (!audioRef.current) {
      audioRef.current = new Audio(audio.url)
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

  function handleRename() {
    if (newName.trim() && newName !== audio.name) {
      onRename(newName.trim())
    }
    setIsRenaming(false)
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-background border border-border hover:border-border/80 transition-colors group">
      {/* Play button */}
      <button onClick={togglePlay}
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors',
          isPlaying ? 'bg-accent text-white' : 'bg-surface-hover text-text-secondary hover:text-accent'
        )}>
        {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
      </button>

      {/* Audio icon + waveform visual */}
      <div className="flex items-center gap-2 shrink-0">
        <Music className="w-4 h-4 text-purple-400" />
        <div className="flex items-end gap-[2px] h-4">
          {[3, 5, 8, 6, 10, 7, 4, 9, 5, 7, 3, 6].map((h, i) => (
            <div key={i} className={cn(
              'w-[2px] rounded-full transition-colors',
              isPlaying ? 'bg-accent animate-pulse' : 'bg-text-secondary/30'
            )} style={{ height: `${h * 1.5}px` }} />
          ))}
        </div>
      </div>

      {/* Name + info */}
      <div className="flex-1 min-w-0">
        {isRenaming ? (
          <div className="flex items-center gap-1">
            <input value={newName} onChange={(e) => setNewName(e.target.value)}
              className="flex-1 bg-surface border border-accent/50 rounded px-2 py-0.5 text-sm text-text-primary focus:outline-none"
              onKeyDown={(e) => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setIsRenaming(false); }}
              autoFocus />
            <button onClick={handleRename} className="text-green-400 hover:text-green-300"><Check className="w-3.5 h-3.5" /></button>
            <button onClick={() => setIsRenaming(false)} className="text-red-400 hover:text-red-300"><X className="w-3.5 h-3.5" /></button>
          </div>
        ) : (
          <p className="text-sm text-text-primary truncate">{audio.name}</p>
        )}
        <div className="flex items-center gap-2 text-xs text-text-secondary/60">
          <span>{formatSize(audio.size)}</span>
          {audio.duration && <span>{formatDuration(audio.duration)}</span>}
        </div>
      </div>

      {/* Actions (hidden during rename) */}
      {!isRenaming && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => { setNewName(audio.name); setIsRenaming(true) }}
            className="p-1.5 rounded text-text-secondary/60 hover:text-text-primary hover:bg-surface-hover transition-colors"
            title="Renomear">
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button onClick={onDownload}
            className="p-1.5 rounded text-text-secondary/60 hover:text-text-primary hover:bg-surface-hover transition-colors"
            title="Download">
            <Download className="w-3.5 h-3.5" />
          </button>
          <button onClick={onDelete}
            className="p-1.5 rounded text-text-secondary/60 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Excluir">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}

export default function AudioUploader({ audios, onAudiosChange, className }: AudioUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<AudioFile | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  function showToast(message: string, type: 'success' | 'error' = 'success') {
    // Use DOM directly to avoid re-render losing the toast
    const existing = document.getElementById('audio-toast')
    if (existing) existing.remove()

    const div = document.createElement('div')
    div.id = 'audio-toast'
    div.style.cssText = 'position:fixed;top:5rem;right:1.5rem;z-index:100;padding:0.875rem 1.25rem;border-radius:0.75rem;display:flex;align-items:center;gap:0.75rem;font-size:0.875rem;font-weight:500;backdrop-filter:blur(12px);border:1px solid;animation:slideIn 0.3s ease-out;'
    div.style.cssText += type === 'success'
      ? 'background:rgba(34,197,94,0.2);border-color:rgba(34,197,94,0.4);color:rgb(134,239,172);'
      : 'background:rgba(239,68,68,0.2);border-color:rgba(239,68,68,0.4);color:rgb(252,165,165);'
    div.innerHTML = `<span>${type === 'success' ? '✓' : '✕'}</span><span>${message}</span>`
    document.body.appendChild(div)
    setTimeout(() => div.remove(), 4000)
  }
  const inputRef = useRef<HTMLInputElement>(null)

  // Load audios from API on mount
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const resp = await listAudios()
        if (cancelled) return
        const loaded: AudioFile[] = resp.audios.map((a) => ({
          id: a.id,
          name: a.name,
          url: getAudioDownloadUrl(a.id),
          size: a.file_size ?? 0,
          duration: a.duration ?? undefined,
        }))
        // Merge: keep temp items, replace/add server items
        onAudiosChange((prev) => {
          const tempItems = prev.filter((a) => a.id.startsWith('temp_'))
          return [...loaded, ...tempItems]
        })
      } catch { /* API not available */ }
    }
    load()
    return () => { cancelled = true }
  }, [])

  async function handleFiles(files: FileList | null) {
    if (!files || isUploading) return

    const audioFiles = Array.from(files).filter(f =>
      f.type.startsWith('audio/') || /\.(mp3|wav|ogg|m4a|aac|flac)$/i.test(f.name)
    )
    if (audioFiles.length === 0) return

    setIsUploading(true)

    for (const file of audioFiles) {
      const blobUrl = URL.createObjectURL(file)
      const tempId = `temp_${Date.now()}_${Math.random().toString(36).slice(2)}`

      // 1. Show instantly
      onAudiosChange((prev) => [...prev, {
        id: tempId,
        name: file.name,
        url: blobUrl,
        size: file.size,
      }])

      // 2. Get duration from browser
      try {
        const audio = new Audio(blobUrl)
        await new Promise<void>((resolve) => {
          audio.onloadedmetadata = () => {
            onAudiosChange((prev) =>
              prev.map((a) => a.id === tempId ? { ...a, duration: audio.duration } : a)
            )
            resolve()
          }
          audio.onerror = () => resolve()
          setTimeout(resolve, 3000)
        })
      } catch { /* non-critical */ }

      // 3. Upload to server
      try {
        const resp = await uploadAudio(file, file.name)
        onAudiosChange((prev) =>
          prev.map((a) => {
            if (a.id === tempId) {
              return {
                id: resp.id,
                name: resp.name,
                url: blobUrl,
                size: resp.file_size ?? file.size,
                duration: resp.duration ?? a.duration,
              }
            }
            return a
          })
        )
        showToast(`Audio "${file.name}" enviado com sucesso!`)
      } catch {
        showToast(`Erro ao enviar "${file.name}"`, 'error')
      }
    }

    setIsUploading(false)
  }

  return (
    <div className={cn('bg-surface border border-border rounded-xl p-4', className)}>
      <div className="flex items-center gap-2 mb-3">
        <Music className="w-4 h-4 text-purple-400" />
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary">
          Audios de Fundo (Background Music)
        </h3>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files) }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-lg px-4 py-2.5 text-center cursor-pointer transition-all duration-200',
          isDragging
            ? 'border-purple-400 bg-purple-500/10'
            : 'border-border/60 hover:border-text-secondary/40 hover:bg-surface-hover/50',
        )}
      >
        <Upload className="w-4 h-4 mx-auto text-text-secondary/50 mb-1" />
        <p className="text-xs text-text-secondary/70">
          Arraste um audio ou clique para selecionar
        </p>
        <p className="text-[10px] text-text-secondary/40 mt-0.5">MP3, WAV, OGG, M4A, AAC</p>
        <input ref={inputRef} type="file" className="hidden" multiple
          accept="audio/*,.mp3,.wav,.ogg,.m4a,.aac,.flac"
          onChange={(e) => handleFiles(e.target.files)} />
      </div>

      {/* Audio list */}
      {audios.length > 0 && (
        <div className="mt-3 space-y-2">
          {audios.map((audio) => (
            <AudioItem
              key={audio.id}
              audio={audio}
              onDelete={() => setDeleteTarget(audio)}
              onRename={(name) => {
                // Optimistic UI update (functional to avoid stale closure)
                onAudiosChange((prev) => prev.map(a => a.id === audio.id ? { ...a, name } : a))
                // API call in background
                if (!audio.id.startsWith('temp_')) {
                  renameAudioApi(audio.id, name).catch(() => {})
                }
              }}
              onDownload={() => { const a = document.createElement('a'); a.href = audio.url; a.download = audio.name; a.click() }}
            />
          ))}
        </div>
      )}

      {audios.length === 0 && (
        <p className="text-xs text-text-secondary/40 mt-1.5 text-center">
          Nenhum audio de fundo adicionado
        </p>
      )}

      {/* Modal de confirmacao de exclusao */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}>
          <div className="bg-surface border border-border rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-red-500/10">
                <AlertTriangle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">Excluir audio</h3>
                <p className="text-xs text-text-secondary">Esta acao nao pode ser desfeita</p>
              </div>
            </div>
            <p className="text-sm text-text-secondary mb-5">
              Tem certeza que deseja excluir <span className="text-text-primary font-medium">"{deleteTarget.name}"</span>?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-hover border border-border text-text-secondary hover:text-text-primary transition-colors">
                Cancelar
              </button>
              <button onClick={async () => {
                const id = deleteTarget.id
                const name = deleteTarget.name
                setDeleteTarget(null)
                if (!id.startsWith('temp_')) {
                  try {
                    await deleteAudioApi(id)
                    showToast(`Audio "${name}" excluido com sucesso!`)
                  } catch (err) {
                    showToast(`Erro ao excluir "${name}"`, 'error')
                    console.error('Failed to delete audio:', err)
                  }
                }
                onAudiosChange((prev) => prev.filter(a => a.id !== id))
              }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 hover:bg-red-600 text-white transition-colors">
                Sim, excluir
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
    </div>
  )
}
