import { useState } from 'react'
import { Lock, AlertTriangle, Loader2 } from 'lucide-react'

interface CookieInputCardProps {
  service: string
  onAdd: (name: string, cookie: string) => Promise<void>
  isAdding: boolean
}

export default function CookieInputCard({ service, onAdd, isAdding }: CookieInputCardProps) {
  const [accountName, setAccountName] = useState('')
  const [cookie, setCookie] = useState('')

  async function handleSubmit() {
    const trimmedName = accountName.trim()
    const trimmedCookie = cookie.trim()
    if (!trimmedName || !trimmedCookie) return
    await onAdd(trimmedName, trimmedCookie)
    setAccountName('')
    setCookie('')
  }

  const serviceLabel = service === 'dreamface' ? 'DreamFace' : 'Grok'

  return (
    <div className="bg-surface border border-border rounded-xl p-5 flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <Lock className="w-5 h-5 text-orange-400" />
        <h3 className="text-sm font-semibold text-text-primary">Manual Cookie Input</h3>
      </div>

      <p className="text-xs text-text-secondary mb-4">
        Use a extensao Cookie Exporter para exportar os cookies do {serviceLabel}.
      </p>

      <input
        value={accountName}
        onChange={(e) => setAccountName(e.target.value)}
        placeholder="Nome da conta (ex: minha-conta-01)"
        className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent mb-3"
      />

      <textarea
        value={cookie}
        onChange={(e) => setCookie(e.target.value)}
        placeholder="Cole o cookie JSON aqui..."
        rows={5}
        className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-xs font-mono resize-none focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent mb-3"
      />

      <div className="flex items-center gap-2 text-xs text-yellow-400 mb-4">
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
        <span>Nota: Token pode expirar diariamente</span>
      </div>

      <button
        onClick={handleSubmit}
        disabled={isAdding || !accountName.trim() || !cookie.trim()}
        className="mt-auto w-full py-2 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isAdding && <Loader2 className="w-4 h-4 animate-spin" />}
        + Add by Cookie
      </button>
    </div>
  )
}
