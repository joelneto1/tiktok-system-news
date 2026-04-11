import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Film, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ReferenceFile } from './ReferenceGallery'

interface ReferenceSelectorProps {
  references: ReferenceFile[]
  selected: string | null
  onSelect: (id: string | null) => void
  className?: string
}

export default function ReferenceSelector({
  references,
  selected,
  onSelect,
  className,
}: ReferenceSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const selectedRef = references.find((r) => r.id === selected)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary mb-1.5">
        Video de Referencia
      </label>

      <div
        className={cn(
          'w-full flex items-center gap-3 rounded-lg bg-background border border-border px-3 py-2.5',
          'text-sm transition-all duration-200',
          'hover:border-text-secondary/40',
          isOpen && 'ring-2 ring-accent/40 border-accent/60',
        )}
      >
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-3 flex-1 min-w-0 text-left"
        >
          {selectedRef ? (
            <>
              <div className="w-8 h-8 rounded bg-surface border border-border overflow-hidden shrink-0 flex items-center justify-center">
                {selectedRef.thumbnailUrl ? (
                  <img src={selectedRef.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                ) : (
                  <Film className="w-3.5 h-3.5 text-text-secondary/40" />
                )}
              </div>
              <span className="text-text-primary truncate flex-1">{selectedRef.name}</span>
            </>
          ) : (
            <span className="text-text-secondary/50 flex-1">Selecione um video de referencia</span>
          )}
          <ChevronDown
            className={cn(
              'w-4 h-4 text-text-secondary shrink-0 transition-transform duration-200',
              isOpen && 'rotate-180',
            )}
          />
        </button>
        {selected && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onSelect(null) }}
            title="Limpar selecao"
            className="p-1 rounded-md text-text-secondary hover:text-red-400 hover:bg-red-500/10 transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-40 mt-1 w-full rounded-lg bg-surface border border-border shadow-xl overflow-hidden">
          {/* None option */}
          <button
            type="button"
            onClick={() => {
              onSelect(null)
              setIsOpen(false)
            }}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left transition-colors',
              'hover:bg-surface-hover',
              !selected && 'bg-accent/5 text-accent',
            )}
          >
            <span className="text-text-secondary/60">Nenhum</span>
          </button>

          {references.map((ref) => (
            <button
              key={ref.id}
              type="button"
              onClick={() => {
                onSelect(ref.id)
                setIsOpen(false)
              }}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left transition-colors',
                'hover:bg-surface-hover',
                selected === ref.id && 'bg-accent/5 text-accent',
              )}
            >
              <div className="w-8 h-8 rounded bg-background border border-border overflow-hidden shrink-0 flex items-center justify-center">
                {ref.thumbnailUrl ? (
                  <img src={ref.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                ) : (
                  <Film className="w-3.5 h-3.5 text-text-secondary/40" />
                )}
              </div>
              <span className="truncate text-text-primary">{ref.name}</span>
            </button>
          ))}

          {references.length === 0 && (
            <div className="px-3 py-4 text-xs text-text-secondary/50 text-center">
              Nenhum video disponivel
            </div>
          )}
        </div>
      )}
    </div>
  )
}
