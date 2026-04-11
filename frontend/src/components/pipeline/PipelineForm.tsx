import { useState, useEffect } from 'react'
import { Play, ListPlus, Globe, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import TopicInput from './TopicInput'
import ReferenceUploader from './ReferenceUploader'
import ReferenceSelector from './ReferenceSelector'
import AudioUploader, { type AudioFile } from './AudioUploader'
import SfxUploader from './SfxUploader'
import AudioSelector from './AudioSelector'
import VideoModelCards from './VideoModelCards'
import type { ReferenceFile } from './ReferenceGallery'
import { startPipeline, enqueuePipeline, type PipelineStartRequest } from '@/api/pipeline'

const LANGUAGES = [
  { code: 'pt-BR', label: 'Portugues (Brasil)' },
  { code: 'en-US', label: 'English (US)' },
  { code: 'es-ES', label: 'Espanol (Espana)' },
  { code: 'fr-FR', label: 'Francais' },
  { code: 'de-DE', label: 'Deutsch' },
] as const

interface PipelineFormProps {
  onSubmit?: (data: PipelineFormData) => void
  onQueue?: (data: PipelineFormData) => void
  className?: string
}

export interface PipelineFormData {
  topic: string
  referenceId: string | null
  language: string
  model: string
}

export default function PipelineForm({ onSubmit, onQueue, className }: PipelineFormProps) {
  const [topic, setTopic] = useState('')
  const [references, setReferences] = useState<ReferenceFile[]>([])
  const [selectedReference, setSelectedReference] = useState<string | null>(null)
  const [language, setLanguage] = useState('pt-BR')
  const [model, setModel] = useState('news_tradicional')
  const [bgAudios, setBgAudios] = useState<AudioFile[]>([])
  const [selectedAudio, setSelectedAudio] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isQueueing, setIsQueueing] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // References are loaded by ReferenceUploader on mount — no need to duplicate here

  function buildRequest(): PipelineStartRequest {
    return {
      topic,
      language,
      model_type: model,
      reference_id: selectedReference ?? undefined,
      audio_id: selectedAudio ?? undefined,
    }
  }

  function buildFormData(): PipelineFormData {
    return {
      topic,
      referenceId: selectedReference,
      language,
      model,
    }
  }

  async function handleSubmit() {
    if (!topic.trim()) return
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      await startPipeline(buildRequest())
      onSubmit?.(buildFormData())
      setTopic('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao iniciar pipeline'
      setSubmitError(msg)
      // Still call onSubmit so parent can handle fallback
      onSubmit?.(buildFormData())
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleQueue() {
    if (!topic.trim()) return
    setIsQueueing(true)
    setSubmitError(null)
    try {
      await enqueuePipeline(buildRequest())
      onQueue?.(buildFormData())
      setTopic('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao adicionar na fila'
      setSubmitError(msg)
      onQueue?.(buildFormData())
    } finally {
      setIsQueueing(false)
    }
  }

  const isValid = topic.trim().length > 0
  const isBusy = isSubmitting || isQueueing

  return (
    <div className={cn('space-y-5', className)}>
      {/* Topic input - full width */}
      <TopicInput value={topic} onChange={setTopic} />

      {/* Upload cards row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ReferenceUploader
          references={references}
          onReferencesChange={setReferences}
        />
        <AudioUploader
          audios={bgAudios}
          onAudiosChange={setBgAudios}
        />
        <SfxUploader />
      </div>

      {/* Config row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <ReferenceSelector
          references={references}
          selected={selectedReference}
          onSelect={setSelectedReference}
        />

        <AudioSelector
          audios={bgAudios}
          selected={selectedAudio}
          onSelect={setSelectedAudio}
        />

        {/* Language selector */}
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-secondary mb-1.5">
            <span className="inline-flex items-center gap-1.5">
              <Globe className="w-3 h-3" />
              Idioma
            </span>
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className={cn(
              'w-full rounded-lg bg-background border border-border px-3 py-2.5',
              'text-sm text-text-primary',
              'focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60',
              'transition-all duration-200 appearance-none',
              'bg-[url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%20width%3D%2716%27%20height%3D%2716%27%20fill%3D%27%2394a3b8%27%20viewBox%3D%270%200%2016%2016%27%3E%3Cpath%20d%3D%27M4.646%206.646a.5.5%200%2001.708%200L8%209.293l2.646-2.647a.5.5%200%2001.708.708l-3%203a.5.5%200%2001-.708%200l-3-3a.5.5%200%20010-.708z%27/%3E%3C/svg%3E")] bg-no-repeat bg-[right_12px_center]',
              '[&>option]:bg-[#111827] [&>option]:text-[#f1f5f9]',
            )}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code} className="bg-[#111827] text-[#f1f5f9]">
                {lang.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Model selection */}
      <VideoModelCards selectedModel={model} onSelect={setModel} />

      {/* Error message */}
      {submitError && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
          {submitError}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!isValid || isBusy}
          className={cn(
            'flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200',
            isValid && !isBusy
              ? 'bg-accent hover:bg-accent-hover text-white shadow-lg shadow-accent/20 hover:shadow-accent/30'
              : 'bg-accent/30 text-white/40 cursor-not-allowed',
          )}
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          Iniciar Pipeline
        </button>

        <button
          type="button"
          onClick={handleQueue}
          disabled={!isValid || isBusy}
          className={cn(
            'flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
            isValid && !isBusy
              ? 'bg-surface border border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover hover:border-text-secondary/30'
              : 'bg-surface/50 border border-border/50 text-text-secondary/30 cursor-not-allowed',
          )}
        >
          {isQueueing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ListPlus className="w-4 h-4" />}
          Adicionar na Fila
        </button>
      </div>
    </div>
  )
}
