import { useState } from 'react'
import { Globe, Loader2, CheckCircle2, ExternalLink, Maximize2, Minimize2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BrowserLoginCardProps {
  service: string
  onAdd: (name: string) => Promise<void>
  isAdding: boolean
}

// noVNC URL on VPS
const NOVNC_URL = 'https://91.98.80.72:6090'

export default function BrowserLoginCard({ service, onAdd, isAdding }: BrowserLoginCardProps) {
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle')
  const [showBrowser, setShowBrowser] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [accountName, setAccountName] = useState('')

  const serviceLabel = service === 'dreamface' ? 'DreamFace' : 'Grok'
  const serviceUrl = service === 'dreamface'
    ? 'https://www.dreamfaceapp.com/avatar'
    : 'https://grok.com/imagine'

  async function handleSaveSession() {
    if (!accountName.trim()) {
      const name = window.prompt(`Nome da conta ${serviceLabel}:`)
      if (!name?.trim()) return
      setAccountName(name.trim())
    }

    setStatus('connecting')
    try {
      await onAdd(accountName.trim() || `${serviceLabel} Account`)
      setStatus('connected')
      setAccountName('')
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold text-text-primary">Browser Login</h3>
        </div>
        <a href={NOVNC_URL} target="_blank" rel="noopener noreferrer"
          className="text-xs text-text-secondary hover:text-accent flex items-center gap-1 transition-colors">
          Abrir em nova aba <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <p className="text-xs text-text-secondary mb-3">
        Faca login no {serviceLabel} pelo navegador remoto, depois clique em <strong>Salvar Sessao</strong>.
      </p>

      {/* noVNC iframe */}
      <div className={cn(
        'bg-black rounded-lg border border-[#1e293b] overflow-hidden mb-3 relative',
        isFullscreen ? 'fixed inset-4 z-50 rounded-xl' : 'aspect-video',
      )}>
        {showBrowser ? (
          <>
            <iframe
              src={NOVNC_URL}
              className="w-full h-full border-0"
              allow="clipboard-read; clipboard-write"
              title={`noVNC - ${serviceLabel}`}
            />
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="absolute top-2 right-2 p-1.5 rounded bg-black/70 text-white/80 hover:text-white transition-colors z-10"
              title={isFullscreen ? 'Minimizar' : 'Tela cheia'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-3 p-4">
            <Globe className="w-8 h-8 text-slate-600" />
            <span className="text-xs text-slate-500 font-mono text-center">
              Clique em "Conectar" para abrir o navegador remoto
            </span>
            <button
              onClick={() => setShowBrowser(true)}
              className="px-4 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-500/30 transition-colors"
            >
              Conectar
            </button>
          </div>
        )}
      </div>

      {/* Fullscreen overlay background */}
      {isFullscreen && (
        <div className="fixed inset-0 bg-black/80 z-40" onClick={() => setIsFullscreen(false)} />
      )}

      {/* Account name + Save Session */}
      <div className="space-y-2 mb-3">
        <input
          type="text"
          value={accountName}
          onChange={(e) => setAccountName(e.target.value)}
          placeholder={`Email ou nome da conta ${serviceLabel}...`}
          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
      </div>

      <div className="flex items-center gap-2 text-xs text-text-secondary mb-3">
        <span>Faca login no navegador acima em <strong className="text-text-primary">{serviceUrl}</strong>, depois clique em Salvar Sessao.</span>
      </div>

      {/* Status indicator */}
      {status === 'connected' && (
        <div className="flex items-center gap-2 text-xs text-green-400 mb-3">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Conta adicionada com sucesso!</span>
        </div>
      )}

      <div className="flex gap-2 mt-auto">
        <button
          onClick={handleSaveSession}
          disabled={isAdding || status === 'connecting' || !accountName.trim()}
          className="flex-1 py-2 px-4 rounded-lg bg-green-500 hover:bg-green-600 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {(isAdding || status === 'connecting') && <Loader2 className="w-4 h-4 animate-spin" />}
          Salvar Sessao
        </button>
        <button
          onClick={() => { setAccountName(''); setStatus('idle') }}
          className="py-2 px-4 rounded-lg bg-red-500/10 text-red-400 text-sm font-medium hover:bg-red-500/20 transition-colors border border-red-500/20"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}
