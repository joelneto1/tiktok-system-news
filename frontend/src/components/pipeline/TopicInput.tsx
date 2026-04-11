import { cn } from '@/lib/utils'

interface TopicInputProps {
  value: string
  onChange: (value: string) => void
  className?: string
}

export default function TopicInput({ value, onChange, className }: TopicInputProps) {
  return (
    <div
      className={cn(
        'rounded-xl bg-surface border border-border p-4 flex flex-col gap-2',
        className,
      )}
    >
      <label className="text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary">
        Topico / Instrucoes do Video
      </label>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ex: Uma explicacao de 30 segundos sobre computacao quantica..."
        rows={3}
        className={cn(
          'w-full resize-y rounded-lg bg-background border border-border px-4 py-2.5',
          'text-sm leading-relaxed text-text-primary placeholder:text-text-secondary/50',
          'focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60',
          'transition-all duration-200 min-h-[72px] max-h-[200px]',
        )}
      />

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-text-secondary/60">
          Descreva o tema, estilo e instrucoes para o video
        </span>
        <span className="text-[11px] text-text-secondary/60 tabular-nums">
          {value.length} caracteres
        </span>
      </div>
    </div>
  )
}
