import { useState } from 'react'
import { RefreshCw, Globe, Trash2, AlertTriangle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface Account {
  id: string
  enabled: boolean
  name: string
  service: string
  credits: string
  proxy: string
  cookieExp: string
  status: 'ACTIVE' | 'CONNECTED' | 'EXPIRED' | 'DISCONNECTED'
}

interface AccountsTableProps {
  accounts: Account[]
  onToggle: (id: string) => void
  onRefresh: (id: string) => void
  onProxySave: (id: string, proxyUrl: string) => void
  onDelete: (id: string) => void
}

const STATUS_STYLES: Record<string, string> = {
  ACTIVE: 'bg-green-500/10 text-green-400 border-green-500/20',
  CONNECTED: 'bg-green-500/10 text-green-400 border-green-500/20',
  EXPIRED: 'bg-red-500/10 text-red-400 border-red-500/20',
  DISCONNECTED: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
}

export default function AccountsTable({
  accounts,
  onToggle,
  onRefresh,
  onProxySave,
  onDelete,
}: AccountsTableProps) {
  const [deleteTarget, setDeleteTarget] = useState<Account | null>(null)
  const [proxyTarget, setProxyTarget] = useState<Account | null>(null)
  const [proxyValue, setProxyValue] = useState('')

  function openProxyModal(account: Account) {
    setProxyTarget(account)
    setProxyValue(account.proxy === '--' ? '' : account.proxy)
  }

  function handleProxySave() {
    if (proxyTarget) {
      onProxySave(proxyTarget.id, proxyValue.trim())
      setProxyTarget(null)
    }
  }

  function confirmDelete() {
    if (deleteTarget) {
      onDelete(deleteTarget.id)
      setDeleteTarget(null)
    }
  }

  return (
    <>
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h3 className="text-sm font-semibold text-text-primary">Active Accounts</h3>
          <span className="text-xs font-mono bg-cyan-500/10 text-cyan-400 px-2.5 py-0.5 rounded-full border border-cyan-500/20">
            {accounts.length}
          </span>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-secondary text-xs">
                <th className="text-left px-4 py-3 font-medium">#</th>
                <th className="text-left px-4 py-3 font-medium">ON/OFF</th>
                <th className="text-left px-4 py-3 font-medium">Account</th>
                <th className="text-left px-4 py-3 font-medium">Service</th>
                <th className="text-left px-4 py-3 font-medium">Credits</th>
                <th className="text-left px-4 py-3 font-medium">Proxy</th>
                <th className="text-left px-4 py-3 font-medium">Cookie Exp</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account, index) => (
                <tr
                  key={account.id}
                  className="border-b border-border/50 hover:bg-surface-hover/50 transition-colors"
                >
                  <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                    {index + 1}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => onToggle(account.id)}
                      className={cn(
                        'relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0',
                        account.enabled ? 'bg-green-500' : 'bg-slate-600',
                      )}
                    >
                      <span
                        className={cn(
                          'absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200',
                          account.enabled && 'translate-x-5',
                        )}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-text-primary font-mono text-xs">
                    {account.name}
                  </td>
                  <td className="px-4 py-3 text-text-secondary text-xs">
                    {account.service === 'dreamface' ? 'DreamFace' : 'Grok'}
                  </td>
                  <td className="px-4 py-3 text-text-primary font-mono text-xs">
                    {account.credits}
                  </td>
                  <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                    {account.proxy}
                  </td>
                  <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                    {account.cookieExp}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
                        STATUS_STYLES[account.status] ?? STATUS_STYLES.DISCONNECTED,
                      )}
                    >
                      {account.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => onRefresh(account.id)}
                        className="p-1.5 rounded-md bg-teal-500/10 text-teal-400 hover:bg-teal-500/20 transition-colors"
                        title="Refresh"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => openProxyModal(account)}
                        className="p-1.5 rounded-md bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                        title="Proxy"
                      >
                        <Globe className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setDeleteTarget(account)}
                        className="p-1.5 rounded-md bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                        title="Excluir"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {accounts.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-text-secondary text-sm">
                    Nenhuma conta cadastrada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="bg-surface border border-border rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-red-500/10">
                <AlertTriangle className="w-5 h-5 text-red-400" />
              </div>
              <h4 className="text-base font-semibold text-text-primary">Excluir conta</h4>
            </div>
            <p className="text-sm text-text-secondary mb-5">
              Tem certeza que deseja excluir{' '}
              <span className="text-text-primary font-medium">
                &quot;{deleteTarget.name}&quot;
              </span>
              ? Esta acao nao pode ser desfeita.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-hover border border-border text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 hover:bg-red-600 text-white transition-colors"
              >
                Sim, excluir
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Proxy edit modal */}
      {proxyTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setProxyTarget(null)}
        >
          <div
            className="bg-surface border border-border rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-base font-semibold text-text-primary">Configurar Proxy</h4>
              <button
                onClick={() => setProxyTarget(null)}
                className="p-1 rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-text-secondary mb-3">
              Proxy para a conta{' '}
              <span className="text-text-primary font-medium">{proxyTarget.name}</span>
            </p>
            <input
              value={proxyValue}
              onChange={(e) => setProxyValue(e.target.value)}
              placeholder="http://user:pass@host:port"
              className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setProxyTarget(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-hover border border-border text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleProxySave}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-accent hover:bg-accent/90 text-white transition-colors"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
