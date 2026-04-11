import { useState, useRef, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Bell, ChevronDown, LogOut, User } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const PAGE_TITLES: Record<string, string> = {
  '/pipeline': 'Pipeline',
  '/videos': 'Videos',
  '/logs': 'Logs',
  '/prompts': 'Prompts',
  '/settings': 'Settings',
  '/connections': 'Conexao',
  '/storage': 'Storage',
}

function getPageTitle(pathname: string): string {
  if (pathname.startsWith('/pipeline/')) return 'Pipeline - Detalhes'
  return PAGE_TITLES[pathname] ?? 'Dashboard'
}

export default function Header() {
  const location = useLocation()
  const { user, logout } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const title = getPageTitle(location.pathname)

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : '??'

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="h-16 border-b border-border bg-surface/50 backdrop-blur-sm flex items-center justify-between px-6 shrink-0">
      {/* Page title */}
      <h1 className="text-xl font-semibold text-text-primary">{title}</h1>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button
          className="relative p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
          title="Notificacoes"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent rounded-full" />
        </button>

        {/* User dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
              <span className="text-xs font-semibold text-accent">
                {initials}
              </span>
            </div>
            <ChevronDown
              className={cn(
                'w-4 h-4 text-text-secondary transition-transform duration-200',
                dropdownOpen && 'rotate-180',
              )}
            />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-surface border border-border rounded-xl shadow-xl shadow-black/20 py-1 z-50">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-sm font-medium text-text-primary">
                  {user?.name ?? 'User'}
                </p>
                <p className="text-xs text-text-secondary truncate">
                  {user?.email ?? ''}
                </p>
              </div>
              <button
                onClick={() => {
                  setDropdownOpen(false)
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
              >
                <User className="w-4 h-4" />
                Perfil
              </button>
              <button
                onClick={() => {
                  setDropdownOpen(false)
                  logout()
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-error hover:bg-surface-hover transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
