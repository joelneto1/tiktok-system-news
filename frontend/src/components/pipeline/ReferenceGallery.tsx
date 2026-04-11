import { useState } from 'react'
import { Play, Pencil, Download, Trash2, AlertTriangle, Check, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ReferenceFile {
  id: string
  name: string
  url: string
  localUrl?: string
  thumbnailUrl?: string
  size: number
  createdAt: string
}

interface ReferenceGalleryProps {
  references: ReferenceFile[]
  onPlay: (ref: ReferenceFile) => void
  onRename: (ref: ReferenceFile, newName: string) => void
  onDownload: (ref: ReferenceFile) => void
  onDelete: (ref: ReferenceFile) => void
  className?: string
}

export default function ReferenceGallery({
  references,
  onPlay,
  onRename,
  onDownload,
  onDelete,
  className,
}: ReferenceGalleryProps) {
  const [deleteTarget, setDeleteTarget] = useState<ReferenceFile | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  function startRename(ref: ReferenceFile) {
    setRenamingId(ref.id)
    setRenameValue(ref.name)
  }

  function confirmRename(ref: ReferenceFile) {
    if (renameValue.trim() && renameValue !== ref.name) {
      onRename(ref, renameValue.trim())
    }
    setRenamingId(null)
  }

  function confirmDelete() {
    if (deleteTarget) {
      onDelete(deleteTarget)
      setDeleteTarget(null)
    }
  }

  if (references.length === 0) {
    return (
      <div className={cn('text-center py-6 text-text-secondary/50 text-xs', className)}>
        Nenhum video de referencia adicionado
      </div>
    )
  }

  return (
    <div className={cn('grid grid-cols-3 gap-3', className)}>
      {references.map((ref) => {
        const isRenaming = renamingId === ref.id

        return (
          <div key={ref.id} className="group relative">
            {/* Thumbnail */}
            <button
              type="button"
              onClick={() => !isRenaming && onPlay(ref)}
              className={cn(
                'relative w-full aspect-square rounded-lg overflow-hidden',
                'bg-background border border-border',
                'hover:border-accent/40 transition-all duration-200',
              )}
            >
              {ref.thumbnailUrl ? (
                <img src={ref.thumbnailUrl} alt={ref.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-background">
                  <Play className="w-5 h-5 text-text-secondary/40" />
                </div>
              )}

              {/* Play overlay on hover */}
              {!isRenaming && (
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div className="w-8 h-8 rounded-full bg-accent/90 flex items-center justify-center">
                    <Play className="w-4 h-4 text-white fill-white" />
                  </div>
                </div>
              )}
            </button>

            {/* Filename / Rename inline */}
            {isRenaming ? (
              <div className="mt-1.5 flex items-center gap-1">
                <input
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') confirmRename(ref)
                    if (e.key === 'Escape') setRenamingId(null)
                  }}
                  autoFocus
                  className="flex-1 min-w-0 bg-surface border border-accent/50 rounded px-1.5 py-0.5 text-[11px] text-text-primary focus:outline-none"
                />
                <button onClick={() => confirmRename(ref)}
                  className="p-0.5 rounded text-green-400 hover:text-green-300 hover:bg-green-500/10 transition-colors shrink-0">
                  <Check className="w-3.5 h-3.5" />
                </button>
                <button onClick={() => setRenamingId(null)}
                  className="p-0.5 rounded text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors shrink-0">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <p className="mt-1.5 text-[11px] text-text-secondary truncate px-0.5" title={ref.name}>
                {ref.name}
              </p>
            )}

            {/* Action buttons on hover (hidden during rename) */}
            {!isRenaming && (
              <div className="absolute top-1 right-1 z-10 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button type="button" onClick={(e) => { e.stopPropagation(); startRename(ref) }}
                  className="p-1.5 rounded bg-black/70 hover:bg-black/90 text-white/80 hover:text-white transition-colors"
                  title="Renomear">
                  <Pencil className="w-3 h-3" />
                </button>
                <button type="button" onClick={(e) => { e.stopPropagation(); onDownload(ref) }}
                  className="p-1.5 rounded bg-black/70 hover:bg-black/90 text-white/80 hover:text-white transition-colors"
                  title="Download">
                  <Download className="w-3 h-3" />
                </button>
                <button type="button" onClick={(e) => { e.stopPropagation(); setDeleteTarget(ref) }}
                  className="p-1.5 rounded bg-black/70 hover:bg-red-600/90 text-white/80 hover:text-white transition-colors"
                  title="Excluir">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        )
      })}

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
                <h3 className="text-sm font-semibold text-text-primary">Excluir referencia</h3>
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
              <button onClick={confirmDelete}
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
