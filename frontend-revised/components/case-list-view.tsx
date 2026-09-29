'use client';

import { useEffect, useState } from 'react';
import { api, ApiOfflineError, CaseSummary } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Dashboard } from './dashboard';
import { NewCaseForm } from './new-case-form';
import { GraphExplorer } from './graph-explorer';
import { EvidenceRegister } from './evidence-register';
import { AuditLog } from './audit-log';
import { WorkspaceView } from './app-shell';

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/70 p-4">
    <h2 className="mb-3 font-mono text-xs tracking-wider text-teal-400">{title}</h2>
    {children}
  </section>
);

export function CaseListView({ initialView = 'dashboard' }: { initialView?: WorkspaceView | 'dashboard' }) {
  const [view, setView] = useState<WorkspaceView | 'dashboard'>(initialView);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [runId, setRunId] = useState<string>();
  const [offline, setOffline] = useState(false);

  const load = () => api.cases().then(setCases).catch(error => setOffline(error instanceof ApiOfflineError));
  
  useEffect(() => { void load(); }, []);
  
  useEffect(() => {
    const listener = (event: Event) => setView((event as CustomEvent<WorkspaceView | 'dashboard'>).detail);
    window.addEventListener('vault-x:navigate', listener);
    return () => window.removeEventListener('vault-x:navigate', listener);
  }, []);

  useEffect(() => {
    const listener = (event: Event) => setRunId((event as CustomEvent<string>).detail);
    window.addEventListener('vault-x:set-run', listener);
    return () => window.removeEventListener('vault-x:set-run', listener);
  }, []);

  const open = async (item: CaseSummary) => {
    try {
      const inv = await api.startInvestigation(item.id);
      setRunId(inv.id);
      setView('detail');
    } catch (error) {
      setOffline(error instanceof ApiOfflineError);
    }
  };

  return (
    <main className="min-h-screen p-4 md:p-6 text-slate-200">
      <div className="mb-4 border border-teal-900 bg-teal-950/30 p-2 font-mono text-xs text-teal-300">
        CASE REPLAY — BITFINEX 2016 PUBLIC DATASET
      </div>
      
      {offline && (
        <div className="mb-4 border border-amber-800 bg-amber-950/20 p-3 font-mono text-xs text-amber-300">
          API OFFLINE — live case data is unavailable; no mock data is displayed.
        </div>
      )}
      
      {view === 'dashboard' && <Dashboard />}
      
      {view === 'list' && (
        <Panel title="CASE REGISTRY">
          <div className="mb-4 flex justify-between items-center">
            <h3 className="text-sm font-medium text-slate-300">Active Investigations</h3>
            <button 
              className="border border-teal-600 bg-teal-950/30 px-4 py-2 font-mono text-xs font-bold tracking-wider text-teal-300 hover:bg-teal-900/40 transition-colors" 
              onClick={() => setView('create')}
            >
              ⚡ NEW INVESTIGATION
            </button>
          </div>
          
          <div className="overflow-hidden rounded border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/80 font-mono text-[10px] text-cyan-400">
                <tr>
                  <th className="p-3">CASE ID</th>
                  <th className="p-3">TITLE</th>
                  <th className="p-3">STATUS</th>
                  <th className="p-3 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-950/30">
                {cases.map(item => (
                  <tr key={item.id} className="hover:bg-slate-800/40 group">
                    <td className="p-3 font-mono text-teal-400">{item.number}</td>
                    <td className="p-3 text-slate-300 group-hover:text-cyan-300 transition-colors">{item.title}</td>
                    <td className="p-3">
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-800/50 bg-teal-950/30 px-2 py-0.5 text-[10px] text-teal-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-teal-500"></span>
                        {item.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button 
                        className="text-xs font-mono text-cyan-500 hover:text-cyan-300 transition-colors"
                        onClick={() => open(item)}
                      >
                        OPEN →
                      </button>
                    </td>
                  </tr>
                ))}
                {cases.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-sm text-slate-500">
                      No cases found. Create a new case to begin tracing.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      
      {view === 'create' && <NewCaseForm onCreated={load} />} 
      {view === 'detail' && <GraphExplorer runId={runId} />} 
      {view === 'evidence' && <EvidenceRegister />} 
      {view === 'vasp' && <Vasps />} 
      {view === 'audit' && <AuditLog />} 
      {view === 'report' && <Reports runId={runId} />} 
      {view === 'sahyog' && <Sahyog attributionId="Xzzx.biz" />}
    </main>
  );
}

function Vasps() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  useEffect(() => { api.vasps().then(result => setItems(result.items)) }, []);
  return (
    <Panel title="VASP INTELLIGENCE">
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {items.map(x => (
          <div key={String(x.name)} className="border border-slate-700 bg-slate-900 p-3">
            <h3 className="font-bold text-cyan-300 mb-1">{String(x.name)}</h3>
            <div className="font-mono text-[10px] text-slate-400 space-y-1">
              <p>Source: <span className="text-slate-300">{String(x.sourceTier)}</span></p>
              <p>Status: <span className="text-amber-400">TIER C / UNVERIFIED</span></p>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Reports({ runId }: { runId?: string }) {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  return (
    <Panel title="REPORTS">
      <div className="flex gap-3 mb-4">
        <button className="border border-teal-800 bg-teal-950/30 px-4 py-2 text-xs font-mono text-teal-300 hover:bg-teal-900/50 transition-colors" onClick={() => runId && api.reports(runId).then(setItems)}>
          GENERATE / LOAD JSON
        </button>
        <button className="border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs font-mono text-slate-300 hover:bg-slate-700 transition-colors" onClick={() => window.open('http://localhost:8000/api/v1/reports/REPORT-CYBER-2026-001/html')}>
          OPEN HTML
        </button>
        <button className="border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs font-mono text-slate-300 hover:bg-slate-700 transition-colors" onClick={() => {
          const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'vaultx-report.json';
          a.click();
        }}>
          DOWNLOAD JSON
        </button>
      </div>
      {items.length > 0 && (
        <pre className="border border-slate-800 bg-slate-900 p-4 text-[10px] font-mono text-slate-400 overflow-auto max-h-96">
          {JSON.stringify(items, null, 2)}
        </pre>
      )}
    </Panel>
  );
}

function Sahyog({ attributionId }: { attributionId: string }) {
  const { user } = useAuth();
  const [reply, setReply] = useState<Record<string, unknown> | null>(null);
  return (
    <Panel title="SAHYOG: MOCK">
      <div className="mb-4 border-l-2 border-amber-500 bg-amber-950/20 p-3 text-sm text-amber-200">
        <strong className="font-mono text-xs">MOCK MODE ACTIVE:</strong> Data is not submitted to any government system. SAHYOG integration is simulated.
      </div>
      <div className="flex gap-3">
        <button className="border border-teal-600 bg-teal-950/40 px-4 py-2 text-xs font-mono font-bold text-teal-300 hover:bg-teal-900/60 transition-colors" onClick={() => api.prepareSahyog(attributionId).then(setReply)}>
          PREPARE MOCK SUBMISSION
        </button>
        {user?.role === 'Supervisor' && (
          <button className="border border-amber-600 bg-amber-950/40 px-4 py-2 text-xs font-mono font-bold text-amber-300 hover:bg-amber-900/60 transition-colors" onClick={() => api.approveSahyog(attributionId).then(setReply)}>
            SUPERVISOR APPROVE
          </button>
        )}
      </div>
      {reply && (
        <div className="mt-4">
          <h3 className="font-mono text-[10px] text-slate-500 mb-2 uppercase">Mock Response Payload</h3>
          <pre className="border border-slate-800 bg-slate-900 p-4 text-[10px] font-mono text-emerald-400 overflow-auto">
            {JSON.stringify(reply, null, 2)}
          </pre>
        </div>
      )}
    </Panel>
  );
}
