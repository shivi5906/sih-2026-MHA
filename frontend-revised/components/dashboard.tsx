'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/70 p-4">
    <h2 className="mb-3 font-mono text-xs tracking-wider text-teal-400">{title}</h2>
    {children}
  </section>
);

export function Dashboard() {
  const [stats, setStats] = useState({ total: 0, active: 0, exchanges: 0, sahyog: 0 });
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    api.cases()
      .then((cases) => {
        setStats({
          total: cases.length,
          active: cases.filter(c => c.status === 'active').length,
          exchanges: 12, // mock data for now
          sahyog: 3 // mock data for now
        });
      })
      .catch(() => setOffline(true));
  }, []);

  const navigate = (view: string) => {
    window.dispatchEvent(new CustomEvent('vault-x:navigate', { detail: view }));
  };

  return (
    <div className="space-y-6">
      {/* System Status */}
      <div className="flex items-center justify-end text-xs font-mono">
        <div className="flex items-center gap-2 rounded border border-slate-800 bg-slate-900/50 px-3 py-1.5">
          <span className="text-slate-400">API STATUS:</span>
          {offline ? (
            <span className="flex items-center gap-1.5 text-amber-500">
              <span className="h-2 w-2 rounded-full bg-amber-500"></span> OFFLINE
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-teal-400">
              <span className="h-2 w-2 rounded-full bg-teal-400 animate-pulse"></span> ONLINE
            </span>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Panel title="TOTAL CASES">
          <div className="text-3xl font-mono text-slate-200">{stats.total}</div>
        </Panel>
        <Panel title="ACTIVE INVESTIGATIONS">
          <div className="text-3xl font-mono text-cyan-400">{stats.active}</div>
        </Panel>
        <Panel title="EXCHANGES IDENTIFIED">
          <div className="text-3xl font-mono text-slate-200">{stats.exchanges}</div>
        </Panel>
        <Panel title="PENDING SAHYOG">
          <div className="text-3xl font-mono text-amber-400">{stats.sahyog}</div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main col */}
        <div className="lg:col-span-2 space-y-6">
          <Panel title="RECENT ACTIVITY">
            <div className="flex h-32 items-center justify-center border border-dashed border-slate-700 bg-slate-900/30 text-sm text-slate-500">
              Recent audit events will appear here
            </div>
          </Panel>
        </div>

        {/* Side col */}
        <div className="space-y-6">
          <Panel title="QUICK ACTIONS">
            <div className="space-y-3">
              <button
                onClick={() => navigate('create')}
                className="flex w-full items-center justify-center gap-2 border border-teal-600 bg-teal-950/30 p-4 text-sm font-bold tracking-wider text-teal-300 hover:bg-teal-900/40 transition-colors"
              >
                ⚡ New Investigation
              </button>
              <button
                onClick={() => navigate('list')}
                className="flex w-full items-center justify-center gap-2 border border-slate-700 bg-slate-900/50 p-4 text-sm font-bold tracking-wider text-slate-300 hover:bg-slate-800 transition-colors"
              >
                📋 View Cases
              </button>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
