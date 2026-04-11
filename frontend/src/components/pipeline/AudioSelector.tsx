import { useState, useRef, useEffect } from 'react'
import { Music, ChevronDown, Play, Pause, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AudioFile } from './AudioUploader'

interface AudioSelectorProps {
  audios: AudioFile[]
  selected: string | null
  onSelect: (id: string | null) => void
  className?: string
}

export default function AudioSelector({ audios, selected, onSelect, className }: AudioSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [playingId, setPlayingId] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const selectedAudio = audios.find(a => a.id === selected)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function togglePreview(audio: AudioFile, e: React.MouseEvent) {
    e.stopPropagation()
    if (playingId === audio.id) {
      audioRef.current?.pause()
      setPlayingId(null)
    } else {
      if (audioRef.current) audioRef.current.pause()
      audioRef.current = new Audio(audio.url)
      audioRef.current.onended = () => setPlayingId(null)
      audioRef.current.play()
      setPlayingId(audio.id)
    }
  }

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary mb-1.5">
        <span className="inline-flex items-center gap-1.5">
          <Music className="w-3 h-3 text-purple-400" />
          Audio de Fundo
        </span>
      </label>
      <div
        className={cn(
          'w-full flex items-center gap-3 rounded-lg bg-background border border-border px-3 py-2.5',
          'text-sm transition-all duration-200',
          'hover:border-text-secondary/40',
          isOpen && 'ring-2 ring-accent/40 border-accent/60',
        )}
      >
        <button type="button" onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-3 flex-1 min-w-0 text-left">
          {selectedAudio ? (
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <div className="w-6 h-6 rounded bg-purple-500/20 flex items-center justify-center shrink-0">
                <Music className="w-3 h-3 text-purple-400" />
              </div>
              <span className="truncate text-text-primary">{selectedAudio.name}</span>
            </div>
          ) : (
            <span className="text-text-secondary/50 flex-1">Selecione um audio de fundo</span>
          )}
          <ChevronDown className={cn('w-4 h-4 text-text-secondary/50 transition-transform', isOpen && 'rotate-180')} />
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

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-lg bg-surface border border-border shadow-xl max-h-60 overflow-y-auto">
          {/* None option */}
          <button onClick={() => { onSelect(null); setIsOpen(false) }}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left transition-colors',
              !selected ? 'bg-accent/10 text-accent' : 'text-text-secondary hover:bg-surface-hover',
            )}>
            <span className="text-text-secondary/50 italic">Sem audio de fundo</span>
          </button>
          {audios.map((audio) => (
            <button key={audio.id} onClick={() => { onSelect(audio.id); setIsOpen(false) }}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left transition-colors',
                selected === audio.id ? 'bg-accent/10 text-accent' : 'text-text-primary hover:bg-surface-hover',
              )}>
              <button onClick={(e) => togglePreview(audio, e)}
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-colors',
                  playingId === audio.id ? 'bg-purple-500 text-white' : 'bg-surface-hover text-text-secondary hover:text-purple-400'
                )}>
                {playingId === audio.id ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
              </button>
              <div className="flex items-end gap-[1px] h-3 shrink-0">
                {[2, 4, 6, 5, 8, 4, 3].map((h, i) => (
                  <div key={i} className={cn('w-[1.5px] rounded-full', playingId === audio.id ? 'bg-purple-400' : 'bg-text-secondary/30')}
                    style={{ height: `${h * 1.2}px` }} />
                ))}
              </div>
              <span className="truncate flex-1">{audio.name}</span>
            </button>
          ))}
          {audios.length === 0 && (
            <div className="px-3 py-4 text-center text-xs text-text-secondary/50">
              Nenhum audio disponivel. Faca upload no card acima.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
