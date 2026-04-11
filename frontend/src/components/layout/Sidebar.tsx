import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Film,
  Terminal,
  FileText,
  Settings,
  Plug,
  HardDrive,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/pipeline', label: 'Pipeline', icon: LayoutDashboard },
  { to: '/videos', label: 'Videos', icon: Film },
  { to: '/logs', label: 'Logs', icon: Terminal },
  { to: '/prompts', label: 'Prompts', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/connections', label: 'Conexao', icon: Plug },
  { to: '/storage', label: 'Storage', icon: HardDrive },
] as const

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, logout } = useAuth()
  const location = useLocation()

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() ?? '??'

  return (
    <aside
      className={cn(
        'flex flex-col h-screen bg-background border-r border-border transition-all duration-300 ease-in-out',
        collapsed ? 'w-[68px]' : 'w-[240px]',
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-border shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
            <LayoutDashboard className="w-4 h-4 text-accent" />
          </div>
          {!collapsed && (
            <span className="text-lg font-bold tracking-tight whitespace-nowrap">
              <span className="text-accent">News</span>
              <span className="text-text-primary">Factory</span>
            </span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
          const isActive =
            location.pathname === to || location.pathname.startsWith(to + '/')

          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150',
                isActive
                  ? 'bg-accent/10 text-accent'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover',
                collapsed && 'justify-center px-0',
              )}
              title={collapsed ? label : undefined}
            >
              <Icon
                className={cn(
                  'w-5 h-5 shrink-0',
                  isActive ? 'text-accent' : 'text-text-secondary',
                )}
              />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 py-2 border-t border-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center w-full py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
          title={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* User info */}
      <div className="px-3 py-3 border-t border-border shrink-0">
        <div
          className={cn(
            'flex items-center gap-3',
            collapsed && 'justify-center',
          )}
        >
          <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-accent">
              {initials}
            </span>
          </div>

          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {user?.name ?? 'User'}
              </p>
              <p className="text-xs text-text-secondary truncate">
                {user?.email ?? ''}
              </p>
            </div>
          )}

          {!collapsed && (
            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-text-secondary hover:text-error hover:bg-surface-hover transition-colors"
              title="Sair"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  )
}
