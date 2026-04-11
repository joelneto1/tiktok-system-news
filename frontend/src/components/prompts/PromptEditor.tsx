import { useState, useEffect, useCallback, useRef } from 'react'
import { Save, Loader2, RotateCcw, Eraser, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface PromptEditorData {
  key: string
  name: string
  description: string
  content: string
  model_type: string | null
  savedContent: string
}

interface PromptEditorProps {
  prompt: PromptEditorData
  onSave: (key: string, content: string) => Promise<void>
  isSaving: boolean
  accentColor: string
  icon: React.ReactNode
}

export default function PromptEditor({
  prompt,
  onSave,
  isSaving,
  accentColor,
  icon,
}: PromptEditorProps) {
  const [content, setContent] = useState(prompt.content)
  const [showSuccess, setShowSuccess] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const hasChanges = content !== prompt.savedContent

  useEffect(() => {
    setContent(prompt.content)
  }, [prompt.content])

  const handleSave = useCallback(async () => {
    if (!hasChanges || isSaving) return
    await onSave(prompt.key, content)
    setShowSuccess(true)
    setTimeout(() => setShowSuccess(false), 2500)
  }, [hasChanges, isSaving, onSave, prompt.key, content])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        if (
          textareaRef.current &&
          document.activeElement === textareaRef.current
        ) {
          e.preventDefault()
          handleSave()
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleSave])

  function handleClear() {
    setContent('')
  }

  function handleRestore() {
    setContent(prompt.savedContent)
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5 space-y-3 transition-all hover:border-border/80">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div
            className={cn(
              'mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
              accentColor === 'cyan' && 'bg-cyan-500/10 text-cyan-400',
              accentColor === 'orange' && 'bg-orange-500/10 text-orange-400',
              accentColor === 'purple' && 'bg-purple-500/10 text-purple-400',
            )}
          >
            {icon}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-text-primary truncate">
                {prompt.name}
              </h4>
              {hasChanges && (
                <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" title="Alteracoes nao salvas" />
              )}
            </div>
            <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">
              {prompt.description}
            </p>
          </div>
        </div>
        {prompt.model_type && (
          <span
            className={cn(
              'text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0',
              accentColor === 'cyan' && 'bg-cyan-500/10 text-cyan-400',
              accentColor === 'orange' && 'bg-orange-500/10 text-orange-400',
              accentColor === 'purple' && 'bg-purple-500/10 text-purple-400',
            )}
          >
            {prompt.model_type.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={10}
        spellCheck={false}
        className="w-full px-4 py-3 rounded-lg bg-[#010409] border border-[#1e293b] text-text-primary placeholder:text-text-secondary/50 text-xs font-mono resize-y focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent leading-relaxed"
      />

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-secondary font-mono tabular-nums">
            {content.length.toLocaleString()} caracteres
          </span>
          {showSuccess && (
            <span className="text-xs text-green-400 flex items-center gap-1 animate-in fade-in">
              <CheckCircle2 className="w-3 h-3" />
              Salvo com sucesso
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <button
              onClick={handleRestore}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1 px-2 py-1 rounded"
            >
              <RotateCcw className="w-3 h-3" />
              Restaurar Padrao
            </button>
          )}
          <button
            onClick={handleClear}
            className="text-xs text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1 px-2 py-1 rounded"
            title="Limpar conteudo"
          >
            <Eraser className="w-3 h-3" />
            Limpar
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5',
              hasChanges && !isSaving
                ? 'bg-cyan-500 hover:bg-cyan-600 text-white'
                : 'bg-surface-hover text-text-secondary cursor-not-allowed',
            )}
          >
            {isSaving ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Save className="w-3 h-3" />
            )}
            {isSaving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}
