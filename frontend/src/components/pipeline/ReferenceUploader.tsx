import { useRef, useState, useCallback, useEffect } from 'react'
import { Upload, Film, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReferenceGallery, { type ReferenceFile } from './ReferenceGallery'
import {
  uploadReference,
  listReferences,
  deleteReference as deleteReferenceApi,
  getReferenceDownloadUrl,
  getReferenceThumbnailUrl,
} from '@/api/references'
// Download/thumbnail endpoints are public (presigned URLs) — no auth needed for <video>/<img> tags

interface ReferenceUploaderProps {
  references: ReferenceFile[]
  onReferencesChange: React.Dispatch<React.SetStateAction<ReferenceFile[]>>
  className?: string
}

const ACCEPTED_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']
const ACCEPTED_EXTENSIONS = '.mp4,.webm,.mov'

// Thumbnail and download endpoints are public (presigned URLs expire in 1h)

export default function ReferenceUploader({
  references,
  onReferencesChange,
  className,
}: ReferenceUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  function showToast(message: string, type: 'success' | 'error' = 'success') {
    const existing = document.getElementById('ref-toast')
    if (existing) existing.remove()

    const div = document.createElement('div')
    div.id = 'ref-toast'
    div.style.cssText = 'position:fixed;top:5rem;right:1.5rem;z-index:100;padding:0.875rem 1.25rem;border-radius:0.75rem;display:flex;align-items:center;gap:0.75rem;font-size:0.875rem;font-weight:500;backdrop-filter:blur(12px);border:1px solid;animation:slideIn 0.3s ease-out;'
    div.style.cssText += type === 'success'
      ? 'background:rgba(34,197,94,0.2);border-color:rgba(34,197,94,0.4);color:rgb(134,239,172);'
      : 'background:rgba(239,68,68,0.2);border-color:rgba(239,68,68,0.4);color:rgb(252,165,165);'
    div.innerHTML = `<span>${type === 'success' ? '✓' : '✕'}</span><span>${message}</span>`
    document.body.appendChild(div)
    setTimeout(() => div.remove(), 4000)
  }
  const [playingRef, setPlayingRef] = useState<ReferenceFile | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Load references from API on mount (merge with any existing temp items)
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const resp = await listReferences()
        if (cancelled) return
        const serverRefs: ReferenceFile[] = resp.references.map((r) => ({
          id: r.id,
          name: r.name || r.original_filename,
          url: getReferenceDownloadUrl(r.id),
          thumbnailUrl: r.thumbnail_path ? getReferenceThumbnailUrl(r.id) : undefined,
          size: r.file_size ?? 0,
          createdAt: r.created_at,
        }))
        // Merge: keep temp items (uploading), replace/add server items
        onReferencesChange((prev) => {
          const tempItems = prev.filter((r) => r.id.startsWith('temp_'))
          return [...serverRefs, ...tempItems]
        })

        // Thumbnails use public presigned URLs — <img> can access directly
      } catch {
        // API not available — keep current references
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleFiles(files: FileList | null) {
    if (!files || isUploading) return

    const validFiles = Array.from(files).filter((f) => ACCEPTED_TYPES.includes(f.type))
    if (validFiles.length === 0) return

    setIsUploading(true)

    for (const file of validFiles) {
      const blobUrl = URL.createObjectURL(file)
      const tempId = `temp_${crypto.randomUUID()}`

      // 1. Show instantly in gallery
      onReferencesChange((prev) => [...prev, {
        id: tempId,
        name: file.name,
        url: blobUrl,
        localUrl: blobUrl,
        size: file.size,
        createdAt: new Date().toISOString(),
      }])

      // 2. Generate thumbnail via Canvas
      try {
        const thumbUrl = await generateVideoThumbnail(blobUrl)
        if (thumbUrl) {
          onReferencesChange((prev) =>
            prev.map((r) => r.id === tempId ? { ...r, thumbnailUrl: thumbUrl } : r)
          )
        }
      } catch { /* non-critical */ }

      // 3. Upload to server in background
      try {
        const ref = await uploadReference(file, file.name)
        // Replace temp with real server data (keep blob URL + thumbnail)
        onReferencesChange((prev) =>
          prev.map((r) => {
            if (r.id === tempId) {
              return {
                id: ref.id,
                name: ref.name || ref.original_filename,
                url: getReferenceDownloadUrl(ref.id),
                localUrl: blobUrl,
                thumbnailUrl: r.thumbnailUrl,
                size: ref.file_size ?? file.size,
                createdAt: ref.created_at,
              }
            }
            return r
          })
        )
        showToast(`Video "${file.name}" enviado com sucesso!`)
      } catch {
        showToast(`Erro ao enviar "${file.name}"`, 'error')
      }
    }

    setIsUploading(false)
  }

  function generateVideoThumbnail(videoUrl: string): Promise<string | null> {
    return new Promise((resolve) => {
      const video = document.createElement('video')
      video.preload = 'metadata'
      video.muted = true
      video.crossOrigin = 'anonymous'
      video.src = videoUrl
      video.onloadeddata = () => { video.currentTime = 0.1 }
      video.onseeked = () => {
        try {
          const canvas = document.createElement('canvas')
          canvas.width = 160
          canvas.height = 284
          const ctx = canvas.getContext('2d')
          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
            resolve(canvas.toDataURL('image/jpeg', 0.7))
          } else {
            resolve(null)
          }
        } catch { resolve(null) }
      }
      video.onerror = () => resolve(null)
      // Timeout after 5 seconds
      setTimeout(() => resolve(null), 5000)
    })
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(true)
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  function handlePlay(ref: ReferenceFile) {
    setPlayingRef(ref)
  }

  function handleRename(ref: ReferenceFile, newName: string) {
    onReferencesChange((prev) =>
      prev.map((r) => (r.id === ref.id ? { ...r, name: newName } : r)),
    )
  }

  function handleDownload(ref: ReferenceFile) {
    const a = document.createElement('a')
    a.href = ref.url
    a.download = ref.name
    a.click()
  }

  async function handleDelete(ref: ReferenceFile) {
    if (!ref.id.startsWith('temp_')) {
      try {
        await deleteReferenceApi(ref.id)
        showToast(`Video "${ref.name}" excluido com sucesso!`)
      } catch (err) {
        showToast(`Erro ao excluir "${ref.name}"`, 'error')
        console.error('Failed to delete reference:', err)
      }
    }
    onReferencesChange((prev) => prev.filter((r) => r.id !== ref.id))
  }

  return (
    <div
      className={cn(
        'rounded-xl bg-surface border border-border p-4 flex flex-col gap-3',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <Film className="w-4 h-4 text-accent" />
        <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary">
          Videos de Referencia
        </span>
        {isLoading && <Loader2 className="w-3 h-3 animate-spin text-text-secondary" />}
      </div>

      {/* Drop zone */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        disabled={isUploading}
        className={cn(
          'w-full rounded-lg border-2 border-dashed px-4 py-3 flex flex-col items-center gap-1.5 transition-all duration-200 cursor-pointer',
          isDragOver
            ? 'border-accent bg-accent/5'
            : 'border-border hover:border-text-secondary/40 hover:bg-surface-hover',
          isUploading && 'opacity-50 cursor-not-allowed',
        )}
      >
        {isUploading ? (
          <Loader2 className="w-5 h-5 animate-spin text-accent" />
        ) : (
          <Upload
            className={cn(
              'w-5 h-5 transition-colors',
              isDragOver ? 'text-accent' : 'text-text-secondary/50',
            )}
          />
        )}
        <span className="text-xs text-text-secondary text-center">
          {isUploading ? 'Enviando...' : 'Arraste um video ou clique para selecionar'}
        </span>
        <span className="text-[10px] text-text-secondary/40">
          MP4, WebM, MOV
        </span>
      </button>

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {/* Gallery */}
      <ReferenceGallery
        references={references}
        onPlay={handlePlay}
        onRename={handleRename}
        onDownload={handleDownload}
        onDelete={handleDelete}
      />

      {/* Video Player Modal */}
      {playingRef && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setPlayingRef(null)}
        >
          <div
            className="relative w-full max-w-2xl mx-4 rounded-xl overflow-hidden bg-background border border-border shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="text-sm text-text-primary font-medium truncate">
                {playingRef.name}
              </span>
              <button
                type="button"
                onClick={() => setPlayingRef(null)}
                className="text-text-secondary hover:text-text-primary text-lg leading-none transition-colors"
              >
                &times;
              </button>
            </div>
            <video
              src={playingRef.localUrl || playingRef.url}
              controls
              autoPlay
              className="w-full max-h-[70vh] bg-black"
            />
          </div>
        </div>
      )}

      <style>{`@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
    </div>
  )
}
