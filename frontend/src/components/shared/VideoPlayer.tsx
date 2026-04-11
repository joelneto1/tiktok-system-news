import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

interface VideoPlayerProps {
  open: boolean
  onClose: () => void
  videoUrl: string
  title?: string
}

export default function VideoPlayer({
  open,
  onClose,
  videoUrl,
  title,
}: VideoPlayerProps) {
  const overlayRef = useRef<HTMLDivElement>(null)

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose()
      }}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-3xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          {title && (
            <h3 className="text-lg font-semibold text-text-primary truncate pr-4">
              {title}
            </h3>
          )}
          <button
            onClick={onClose}
            className="ml-auto p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors bg-surface/80"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Video */}
        <div className="rounded-xl overflow-hidden bg-black border border-border shadow-2xl shadow-black/40">
          <video
            src={videoUrl}
            controls
            autoPlay
            className="w-full aspect-video"
          >
            Seu navegador nao suporta a tag de video.
          </video>
        </div>
      </div>
    </div>
  )
}
