import { cn } from '@/lib/utils'

type Status = 'completed' | 'processing' | 'queued' | 'failed' | 'expired' | string

interface StatusBadgeProps {
  status: Status
  size?: 'sm' | 'md'
}

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-success/15 text-success border-success/20',
  processing: 'bg-accent/15 text-accent border-accent/20 animate-pulse',
  queued: 'bg-text-secondary/15 text-text-secondary border-text-secondary/20',
  failed: 'bg-error/15 text-error border-error/20',
  expired: 'bg-error/15 text-error border-error/20',
}

const STATUS_LABELS: Record<string, string> = {
  completed: 'Concluido',
  processing: 'Processando',
  queued: 'Na fila',
  failed: 'Falhou',
  expired: 'Expirado',
}

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.queued
  const label = STATUS_LABELS[status] ?? status

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium capitalize',
        style,
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
      )}
    >
      {label}
    </span>
  )
}
