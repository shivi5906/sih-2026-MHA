'use client';

import { useState, useEffect } from 'react';
import { Menu, X, LogOut, ChevronDown, LayoutList, Plus, Network, FileCheck2, Building2, ScrollText, FileText, Send, Bot, LayoutDashboard } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';

export type WorkspaceView = 'dashboard' | 'list' | 'create' | 'detail' | 'evidence' | 'vasp' | 'audit' | 'report' | 'sahyog';

interface AppShellProps {
  children: React.ReactNode;
  currentCaseId?: string;
}

const navItems: { label: string; view: WorkspaceView; icon: React.ElementType }[] = [
  { label: 'Dashboard', view: 'dashboard', icon: LayoutList }, // Using LayoutList for Dashboard as temporary since LayoutDashboard isn't imported
  { label: 'Case registry', view: 'list', icon: LayoutList },
  { label: 'Create case', view: 'create', icon: Plus },
  { label: 'Graph explorer', view: 'detail', icon: Network },
  { label: 'Evidence register', view: 'evidence', icon: FileCheck2 },
  { label: 'VASP intelligence', view: 'vasp', icon: Building2 },
  { label: 'Audit log', view: 'audit', icon: ScrollText },
  { label: 'Reports', view: 'report', icon: FileText },
  { label: 'SAHYOG preparation', view: 'sahyog', icon: Send },
];

export function AppShell({ children, currentCaseId }: AppShellProps) {
  const navigate = (view: WorkspaceView) => window.dispatchEvent(new CustomEvent('vault-x:navigate', { detail: view }));
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentView, setCurrentView] = useState<WorkspaceView>('dashboard');

  useEffect(() => {
    const listener = (e: Event) => setCurrentView((e as CustomEvent<WorkspaceView>).detail);
    window.addEventListener('vault-x:navigate', listener);
    return () => window.removeEventListener('vault-x:navigate', listener);
  }, []);

  const currentCase = null;

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      {/* Top bar */}
      <div className="fixed top-0 left-0 right-0 h-14 bg-slate-900/95 border-b border-slate-700/50 flex items-center px-4 gap-4 z-40">
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1 hover:bg-slate-800 rounded transition-colors md:hidden">
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        {/* Logo */}
        <div className="flex items-center gap-2 font-bold tracking-tight text-sm">
          <div className="w-6 h-6 border border-cyan-700/50 flex items-center justify-center rounded-sm hidden md:flex">
            <span className="text-xs font-mono text-cyan-700">V</span>
          </div>
          <span className="hidden md:inline">VAULT-X</span>
        </div>

        {/* Case context */}
        {currentCase && (
          <div className="hidden md:flex items-center gap-3 ml-auto mr-auto flex-1 max-w-xs">
            <div className="px-2 py-1 bg-slate-800/50 border border-slate-700/30 rounded text-xs">
              <div className="text-slate-400 text-xs font-mono mb-0.5">Case</div>
              <div className="text-slate-50 text-xs font-mono truncate">{currentCase.number}</div>
            </div>
            <div className="text-slate-500 text-xs">•</div>
            <div className="px-2 py-1 bg-slate-800/50 border border-slate-700/30 rounded text-xs flex-1">
              <div className="text-slate-400 text-xs font-mono mb-0.5">Risk</div>
              <div className={`text-xs font-mono ${currentCase.riskLevel === 'critical' ? 'text-red-400' : currentCase.riskLevel === 'high' ? 'text-orange-400' : 'text-slate-400'}`}>
                {currentCase.riskLevel.toUpperCase()}
              </div>
            </div>
          </div>
        )}

        {/* User menu */}
        <div className="ml-auto flex items-center gap-3">
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-1 hover:bg-slate-800 rounded transition-colors text-sm"
            >
              <div className="w-6 h-6 bg-slate-700 rounded flex items-center justify-center text-xs font-bold">{user?.name.charAt(0).toUpperCase()}</div>
              <span className="hidden md:inline text-xs font-mono text-slate-300">{user?.email.split('@')[0]}</span>
              <ChevronDown size={14} className="text-slate-500" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-1 w-40 bg-slate-800 border border-slate-700 rounded shadow-lg z-50">
                <div className="p-2 border-b border-slate-700">
                  <div className="text-xs text-slate-400 font-mono mb-1">Role</div>
                  <div className="text-sm text-slate-50">{user?.role}</div>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-700/50 flex items-center gap-2 transition-colors"
                >
                  <LogOut size={14} />
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex pt-14">
        {/* Left sidebar */}
        <div
          className={`${
            sidebarOpen ? 'w-56' : 'w-0'
          } bg-slate-900 border-r border-slate-700/50 overflow-hidden transition-all duration-300 hidden md:block`}
        >
          <nav className="p-4 space-y-1">
            <div className="text-[10px] text-slate-600 font-mono uppercase tracking-[0.18em] mb-4 px-2">Operations</div>
            {navItems.map(({ label, view, icon: Icon }) => {
              if (Icon === LayoutList && view === 'dashboard') Icon = LayoutDashboard;
              const isActive = currentView === view;
              return (
                <button 
                  key={view} 
                  onClick={() => navigate(view)} 
                  className={`w-full flex items-center gap-3 text-left px-3 py-2 text-[11px] font-mono transition-colors ${
                    isActive 
                      ? 'bg-slate-800/50 border-l-2 border-cyan-700/60 text-slate-50' 
                      : 'text-slate-400 hover:bg-slate-800/40 hover:text-teal-300'
                  }`}
                >
                  <Icon size={14} strokeWidth={1.5} className={isActive ? 'text-cyan-400' : 'text-slate-600'} />
                  <span>{label}</span>
                </button>
              );
            })}
            <div className="mt-8 border-t border-slate-800/80 pt-4 px-3">
              <button onClick={() => navigate('detail')} className="flex items-center gap-3 text-[11px] font-mono text-slate-500 hover:text-teal-300 transition-colors">
                <Bot size={14} /> Investigator assistant
              </button>
            </div>
          </nav>
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden">
          {/* Breadcrumb bar */}
          <div className="h-8 border-b border-slate-800 bg-slate-900/40 flex items-center px-4 md:px-6">
            <div className="font-mono text-[10px] text-slate-500 flex items-center gap-2">
              <span className="text-slate-400">VAULT-X</span>
              <span className="text-slate-600">/</span>
              <span className="text-cyan-600/80 uppercase tracking-wider">{navItems.find(i => i.view === currentView)?.label || 'Workspace'}</span>
            </div>
          </div>
          
          <div className="flex-1 overflow-auto">{children}</div>
        </div>
      </div>
    </div>
  );
}

function NavItem({ label, icon, active = false }: { label: string; icon: string; active?: boolean }) {
  return (
    <button
      className={`w-full text-left px-3 py-2 text-sm font-mono transition-colors ${
        active
          ? 'bg-slate-800/50 border-l-2 border-cyan-700/60 text-slate-50'
          : 'text-slate-400 hover:bg-slate-800/30 hover:text-slate-300'
      }`}
    >
      <span className="inline-block w-5">{icon}</span>
      <span>{label}</span>
    </button>
  );
}
