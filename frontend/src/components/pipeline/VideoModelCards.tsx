import { Tv, Newspaper, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { VIDEO_MODELS } from '@/lib/constants'

interface VideoModelCardsProps {
  selectedModel: string
  onSelect: (modelId: string) => void
  className?: string
}

const MODEL_META: Record<string, { icon: typeof Tv; description: string }> = {
  news_tradicional: {
    icon: Tv,
    description: 'B-rolls sobre o avatar com legendas',
  },
  news_jornalistico: {
    icon: Newspaper,
    description: 'Avatar PiP + B-rolls Fundo + Motion Graphics',
  },
  news_ice: {
    icon: Zap,
    description: 'Estilo ICE de alta retencao',
  },
}

export default function VideoModelCards({
  selectedModel,
  onSelect,
  className,
}: VideoModelCardsProps) {
  return (
    <div className={cn('space-y-2', className)}>
      <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary">
        Modelo do Video
      </label>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {VIDEO_MODELS.map((model) => {
          const meta = MODEL_META[model.id]
          const Icon = meta?.icon ?? Tv
          const description = meta?.description ?? model.description
          const isSelected = selectedModel === model.id
          const isDisabled = !model.active

          return (
            <button
              key={model.id}
              type="button"
              onClick={() => {
                if (!isDisabled) onSelect(model.id)
              }}
              disabled={isDisabled}
              className={cn(
                'relative flex flex-col items-start gap-2.5 rounded-xl border p-3.5 text-left transition-all duration-200',
                isSelected
                  ? 'border-accent bg-accent/5 shadow-[0_0_20px_-4px_rgba(6,182,212,0.25)]'
                  : 'border-border bg-surface hover:bg-surface-hover hover:border-text-secondary/30',
                isDisabled && 'opacity-45 cursor-not-allowed hover:bg-surface hover:border-border',
              )}
            >
              {/* Coming soon badge */}
              {'comingSoon' in model && model.comingSoon && (
                <span className="absolute top-3 right-3 text-[9px] font-bold uppercase tracking-wider text-text-secondary bg-background border border-border rounded-full px-2 py-0.5">
                  Em Breve
                </span>
              )}

              {/* Icon */}
              <div
                className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center',
                  isSelected ? 'bg-accent/15' : 'bg-background',
                )}
              >
                <Icon
                  className={cn(
                    'w-4.5 h-4.5',
                    isSelected ? 'text-accent' : 'text-text-secondary',
                  )}
                />
              </div>

              {/* Text */}
              <div className="space-y-1">
                <h3
                  className={cn(
                    'text-sm font-semibold',
                    isSelected ? 'text-accent' : 'text-text-primary',
                  )}
                >
                  {model.name}
                </h3>
                <p className="text-[11px] leading-relaxed text-text-secondary">
                  {description}
                </p>
              </div>

              {/* Selected indicator */}
              {isSelected && (
                <div className="absolute bottom-3 right-3 w-2 h-2 rounded-full bg-accent shadow-[0_0_6px_rgba(6,182,212,0.6)]" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
