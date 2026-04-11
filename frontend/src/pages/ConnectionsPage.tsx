import { useState, useEffect, useCallback } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import BrowserLoginCard from '@/components/connections/BrowserLoginCard'
import CookieInputCard from '@/components/connections/CookieInputCard'
import AccountsTable, { type Account } from '@/components/connections/AccountsTable'
import {
  listAccounts,
  addAccount as addAccountApi,
  toggleAccount as toggleAccountApi,
  refreshAccount as refreshAccountApi,
  updateAccount as updateAccountApi,
  deleteAccount as deleteAccountApi,
  type ConnectionAccount,
} from '@/api/connections'

/* ── Tabs: display label -> API service value ── */
const TABS = [
  { label: 'DreamFace', value: 'dreamface' },
  { label: 'Grok', value: 'grok' },
] as const

type TabValue = (typeof TABS)[number]['value']

/* ── DOM toast (same pattern as AudioUploader) ── */
function showToast(message: string, type: 'success' | 'error' = 'success') {
  const existing = document.getElementById('conn-toast')
  if (existing) existing.remove()

  const div = document.createElement('div')
  div.id = 'conn-toast'
  div.style.cssText =
    'position:fixed;top:5rem;right:1.5rem;z-index:100;padding:0.875rem 1.25rem;border-radius:0.75rem;display:flex;align-items:center;gap:0.75rem;font-size:0.875rem;font-weight:500;backdrop-filter:blur(12px);border:1px solid;animation:slideIn 0.3s ease-out;'
  div.style.cssText +=
    type === 'success'
      ? 'background:rgba(34,197,94,0.2);border-color:rgba(34,197,94,0.4);color:rgb(134,239,172);'
      : 'background:rgba(239,68,68,0.2);border-color:rgba(239,68,68,0.4);color:rgb(252,165,165);'
  div.innerHTML = `<span>${type === 'success' ? '\u2713' : '\u2715'}</span><span>${message}</span>`
  document.body.appendChild(div)
  setTimeout(() => div.remove(), 4000)
}

/* ── Map backend -> frontend model ── */
function mapApiAccount(a: ConnectionAccount): Account {
  return {
    id: a.id,
    enabled: a.is_active,
    name: a.account_name,
    service: a.service,
    credits: String(a.credits),
    proxy: a.proxy_url ?? '--',
    cookieExp: a.cookie_expires_at ?? '--',
    status: a.status.toUpperCase() as Account['status'],
  }
}

export default function ConnectionsPage() {
  const [activeTab, setActiveTab] = useState<TabValue>('dreamface')
  const [accounts, setAccounts] = useState<Account[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAdding, setIsAdding] = useState(false)

  /* ── Fetch ── */
  const fetchAccounts = useCallback(async () => {
    try {
      const list = await listAccounts()
      setAccounts(list.map(mapApiAccount))
    } catch {
      setAccounts([])
    }
  }, [])

  useEffect(() => {
    fetchAccounts().finally(() => setIsLoading(false))
  }, [fetchAccounts])

  const filteredAccounts = accounts.filter((a) => a.service === activeTab)

  /* ── Add account via Browser card ── */
  async function handleBrowserAdd(name: string) {
    setIsAdding(true)
    try {
      const created = await addAccountApi({
        service: activeTab,
        account_name: name,
      })
      setAccounts((prev) => [...prev, mapApiAccount(created)])
      showToast(`Conta "${name}" adicionada com sucesso!`)
    } catch {
      showToast('Erro ao adicionar conta', 'error')
      throw new Error('add failed')
    } finally {
      setIsAdding(false)
    }
  }

  /* ── Add account via Cookie card ── */
  async function handleCookieAdd(name: string, cookie: string) {
    setIsAdding(true)
    try {
      const created = await addAccountApi({
        service: activeTab,
        account_name: name,
        cookies_json: cookie,
      })
      setAccounts((prev) => [...prev, mapApiAccount(created)])
      showToast(`Conta "${name}" adicionada com sucesso!`)
    } catch {
      showToast('Erro ao adicionar conta por cookie', 'error')
    } finally {
      setIsAdding(false)
    }
  }

  /* ── Toggle ── */
  async function handleToggle(id: string) {
    setAccounts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, enabled: !a.enabled } : a)),
    )
    try {
      const updated = await toggleAccountApi(id)
      setAccounts((prev) =>
        prev.map((a) => (a.id === id ? mapApiAccount(updated) : a)),
      )
      const acct = accounts.find((a) => a.id === id)
      showToast(
        `Conta "${acct?.name}" ${updated.is_active ? 'ativada' : 'desativada'}`,
      )
    } catch {
      setAccounts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, enabled: !a.enabled } : a)),
      )
      showToast('Erro ao alterar status', 'error')
    }
  }

  /* ── Refresh ── */
  async function handleRefresh(id: string) {
    try {
      await refreshAccountApi(id)
      await fetchAccounts()
      const acct = accounts.find((a) => a.id === id)
      showToast(`Conta "${acct?.name}" verificada com sucesso!`)
    } catch {
      showToast('Erro ao verificar conta', 'error')
    }
  }

  /* ── Proxy ── */
  async function handleProxySave(id: string, proxyUrl: string) {
    try {
      const updated = await updateAccountApi(id, {
        proxy_url: proxyUrl || null,
      })
      setAccounts((prev) =>
        prev.map((a) => (a.id === id ? mapApiAccount(updated) : a)),
      )
      showToast('Proxy atualizado com sucesso!')
    } catch {
      showToast('Erro ao atualizar proxy', 'error')
    }
  }

  /* ── Delete ── */
  async function handleDelete(id: string) {
    const acct = accounts.find((a) => a.id === id)
    try {
      await deleteAccountApi(id)
      setAccounts((prev) => prev.filter((a) => a.id !== id))
      showToast(`Conta "${acct?.name}" excluida com sucesso!`)
    } catch {
      showToast('Erro ao excluir conta', 'error')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-text-primary">
          Conexao
        </h2>
        <p className="text-text-secondary text-sm mt-1">
          Gerencie suas sessoes e configuracoes de proxy.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={cn(
              'px-4 py-2 rounded-md text-sm font-medium transition-colors',
              activeTab === tab.value
                ? 'bg-accent/10 text-accent'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Login cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BrowserLoginCard
          service={activeTab}
          onAdd={handleBrowserAdd}
          isAdding={isAdding}
        />
        <CookieInputCard
          service={activeTab}
          onAdd={handleCookieAdd}
          isAdding={isAdding}
        />
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-accent" />
          <span className="ml-2 text-sm text-text-secondary">Carregando...</span>
        </div>
      ) : (
        <AccountsTable
          accounts={filteredAccounts}
          onToggle={handleToggle}
          onRefresh={handleRefresh}
          onProxySave={handleProxySave}
          onDelete={handleDelete}
        />
      )}
    </div>
  )
}
