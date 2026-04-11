import { useState, useEffect } from 'react'
import { Loader2, FileText, Video, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import PromptEditor, {
  type PromptEditorData,
} from '@/components/prompts/PromptEditor'
import { listPrompts, updatePrompt } from '@/api/prompts'

/* ─────────────────────────────────────────────
   Model Tabs Configuration
   ───────────────────────────────────────────── */

interface ModelTab {
  id: string
  label: string
  accent: 'cyan' | 'orange' | 'purple'
  badge?: string
}

const MODEL_TABS: ModelTab[] = [
  { id: 'news_tradicional', label: 'News Tradicional', accent: 'cyan' },
  {
    id: 'news_jornalistico',
    label: 'News Jornalistico',
    accent: 'orange',
    badge: 'Em Breve',
  },
  {
    id: 'news_ice',
    label: 'News ICE',
    accent: 'purple',
    badge: 'Em Breve',
  },
]

/* ─────────────────────────────────────────────
   Prompt Icon Selector
   ───────────────────────────────────────────── */

function promptIcon(key: string) {
  if (key.includes('roteirista')) return <FileText className="w-4 h-4" />
  if (key.includes('diretor')) return <Video className="w-4 h-4" />
  if (key.includes('prompter')) return <Sparkles className="w-4 h-4" />
  return <FileText className="w-4 h-4" />
}

/* ─────────────────────────────────────────────
   Tab Button
   ───────────────────────────────────────────── */

function TabButton({
  tab,
  isActive,
  onClick,
  promptCount,
}: {
  tab: ModelTab
  isActive: boolean
  onClick: () => void
  promptCount: number
}) {
  const accentClasses = {
    cyan: {
      active: 'border-cyan-400 text-cyan-400',
      hover: 'hover:text-cyan-400/70 hover:border-cyan-400/30',
      badge: 'bg-cyan-500/10 text-cyan-400',
    },
    orange: {
      active: 'border-orange-400 text-orange-400',
      hover: 'hover:text-orange-400/70 hover:border-orange-400/30',
      badge: 'bg-orange-500/10 text-orange-400',
    },
    purple: {
      active: 'border-purple-400 text-purple-400',
      hover: 'hover:text-purple-400/70 hover:border-purple-400/30',
      badge: 'bg-purple-500/10 text-purple-400',
    },
  }

  const colors = accentClasses[tab.accent]

  return (
    <button
      onClick={onClick}
      className={cn(
        'px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 whitespace-nowrap',
        isActive
          ? colors.active
          : `border-transparent text-text-secondary ${colors.hover}`,
      )}
    >
      {tab.label}
      {tab.badge && (
        <span
          className={cn(
            'text-[10px] font-semibold px-1.5 py-0.5 rounded-full',
            colors.badge,
          )}
        >
          {tab.badge}
        </span>
      )}
      {promptCount > 0 && (
        <span className="text-[10px] text-text-secondary bg-surface-hover px-1.5 py-0.5 rounded-full">
          {promptCount}
        </span>
      )}
    </button>
  )
}

/* ─────────────────────────────────────────────
   Main Page Component
   ───────────────────────────────────────────── */

export default function PromptsPage() {
  const [promptsByModel, setPromptsByModel] = useState<
    Record<string, PromptEditorData[]>
  >({})
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('news_tradicional')
  const [savingKeys, setSavingKeys] = useState<Set<string>>(new Set())

  useEffect(() => {
    async function load() {
      try {
        const prompts = await listPrompts()
        const grouped: Record<string, PromptEditorData[]> = {}
        for (const p of prompts) {
          const modelType = p.model_type ?? 'shared'
          if (!grouped[modelType]) grouped[modelType] = []
          grouped[modelType].push({
            key: p.key,
            name: p.name,
            description: p.description ?? '',
            content: p.content,
            model_type: p.model_type,
            savedContent: p.content,
          })
        }
        setPromptsByModel(grouped)
      } catch {
        setPromptsByModel({})
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  async function handleSave(key: string, content: string) {
    setSavingKeys((prev) => new Set(prev).add(key))
    try {
      await updatePrompt(key, content)
      // Update saved content to reflect new baseline
      setPromptsByModel((prev) => {
        const updated = { ...prev }
        for (const model of Object.keys(updated)) {
          updated[model] = updated[model].map((p) =>
            p.key === key ? { ...p, content, savedContent: content } : p,
          )
        }
        return updated
      })
    } catch {
      console.error('Failed to save prompt', key)
    } finally {
      setSavingKeys((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
        <span className="ml-2 text-text-secondary">
          Carregando prompts...
        </span>
      </div>
    )
  }

  const activePrompts = promptsByModel[activeTab] ?? []
  const activeTabConfig = MODEL_TABS.find((t) => t.id === activeTab)

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          <span className="text-text-primary">System </span>
          <span className="text-cyan-400">Prompts</span>
        </h2>
        <p className="text-text-secondary text-sm mt-1">
          Configure os prompts de IA para cada modelo de video
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-border overflow-x-auto">
        <div className="flex gap-0">
          {MODEL_TABS.map((tab) => (
            <TabButton
              key={tab.id}
              tab={tab}
              isActive={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              promptCount={(promptsByModel[tab.id] ?? []).length}
            />
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activePrompts.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <div className="w-12 h-12 mx-auto rounded-xl bg-surface-hover flex items-center justify-center">
            <FileText className="w-6 h-6 text-text-secondary" />
          </div>
          <div>
            <p className="text-text-secondary text-sm">
              Nenhum prompt encontrado para{' '}
              <span className="font-medium text-text-primary">
                {activeTabConfig?.label}
              </span>
            </p>
            <p className="text-text-secondary/60 text-xs mt-1">
              Os prompts serao criados automaticamente ao reiniciar o backend.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {activePrompts.map((prompt) => (
            <PromptEditor
              key={prompt.key}
              prompt={prompt}
              onSave={handleSave}
              isSaving={savingKeys.has(prompt.key)}
              accentColor={activeTabConfig?.accent ?? 'cyan'}
              icon={promptIcon(prompt.key)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
