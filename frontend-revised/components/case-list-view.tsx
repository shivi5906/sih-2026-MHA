'use client';

import { useEffect, useState } from 'react';
import { api, apiErrorMessage, ApiOfflineError, CaseSummary, DocumentSummary, Officer } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Dashboard } from './dashboard';
import { NewCaseForm } from './new-case-form';
import { GraphExplorer } from './graph-explorer';
import { EvidenceRegister } from './evidence-register';
import { AuditLog } from './audit-log';
import { WorkspaceView } from './app-shell';
import { openPdf, StatusChip } from './notice-composer';

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/80 p-5 shadow-lg">
    <h2 className="mb-4 font-mono text-sm font-bold tracking-wider text-teal-400 uppercase">{title}</h2>
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
    <main className="min-h-screen p-4 md:p-6 text-slate-100 text-sm">
      <div className="mb-4 border border-teal-800 bg-teal-950/40 p-2.5 font-mono text-xs font-semibold text-teal-300 flex items-center justify-between">
        <span>CASE REPLAY — FORENSIC WORKSTATION ACTIVE</span>
        <span className="text-[11px] text-teal-400/80">SECTION 63 BSA & 94 BNSS READY</span>
      </div>
      
      {offline && (
        <div className="mb-4 border border-amber-800 bg-amber-950/40 p-3 font-mono text-xs font-medium text-amber-300">
          API OFFLINE — live case data is unavailable; no mock data is displayed.
        </div>
      )}
      
      {view === 'dashboard' && <Dashboard />}
      
      {view === 'list' && (
        <Panel title="CASE REGISTRY">
          <div className="mb-4 flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-200">Active Investigations & FIRs</h3>
            <button 
              className="border border-teal-500 bg-teal-950/60 px-4 py-2 font-mono text-xs font-bold tracking-wider text-teal-300 hover:bg-teal-900/60 transition-colors shadow" 
              onClick={() => setView('create')}
            >
              ⚡ NEW INVESTIGATION
            </button>
          </div>
          
          <div className="overflow-hidden rounded border border-slate-800 bg-slate-900/30">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/90 font-mono text-xs font-bold text-cyan-300 border-b border-slate-800">
                <tr>
                  <th className="p-3.5">CASE ID / FIR</th>
                  <th className="p-3.5">TITLE</th>
                  <th className="p-3.5">STATUS</th>
                  <th className="p-3.5 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {cases.map(item => (
                  <tr key={item.id} className="hover:bg-slate-800/50 group transition-colors">
                    <td className="p-3.5 font-mono font-bold text-teal-300">{item.number}</td>
                    <td className="p-3.5 text-slate-200 font-medium group-hover:text-cyan-200 transition-colors">{item.title}</td>
                    <td className="p-3.5">
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-700/60 bg-teal-950/50 px-2.5 py-0.5 text-xs font-mono font-medium text-teal-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-teal-400"></span>
                        {item.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-3.5 text-right">
                      <button 
                        className="text-xs font-mono font-bold text-cyan-400 hover:text-cyan-200 transition-colors border border-cyan-800/60 bg-cyan-950/30 px-3 py-1.5 rounded hover:bg-cyan-900/50"
                        onClick={() => open(item)}
                      >
                        OPEN INVESTIGATION →
                      </button>
                    </td>
                  </tr>
                ))}
                {cases.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-sm text-slate-400">
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
      {view === 'report' && <Reports runId={runId} cases={cases} onSelectRun={setRunId} />} 
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
          <div key={String(x.name)} className="border border-slate-700 bg-slate-900 p-4 shadow">
            <h3 className="font-bold text-cyan-300 text-sm mb-1.5">{String(x.name)}</h3>
            <div className="font-mono text-xs text-slate-400 space-y-1">
              <p>Source Tier: <span className="text-slate-200 font-semibold">{String(x.sourceTier)}</span></p>
              <p>Status: <span className="text-amber-400 font-semibold">TIER C / UNVERIFIED</span></p>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

const OFFICER_KEY = 'vault-x-officer';

function loadOfficer(): Officer {
  try { return JSON.parse(window.localStorage.getItem(OFFICER_KEY) || '{}'); } catch { return {}; }
}

function saveOfficer(officer: Officer) {
  try { window.localStorage.setItem(OFFICER_KEY, JSON.stringify(officer)); } catch { /* ignore */ }
}

function Reports({ runId, cases, onSelectRun }: { runId?: string; cases?: CaseSummary[]; onSelectRun?: (id: string) => void }) {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | undefined>(runId);
  const [officer, setOfficer] = useState<Officer>({ name: '', rank: '', unit: '', email: '', phone: '' });
  const [courtName, setCourtName] = useState("HON'BLE SPECIAL COURT FOR ECONOMIC OFFENCES & CYBER CRIME");
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    setActiveRunId(runId);
  }, [runId]);

  useEffect(() => {
    setOfficer(loadOfficer());
  }, []);

  const loadDocuments = (targetRunId?: string) => {
    const rid = targetRunId || activeRunId;
    if (!rid) return;
    api.documents(rid)
      .then(setDocuments)
      .catch(() => undefined);
  };

  useEffect(() => {
    if (activeRunId) {
      loadDocuments(activeRunId);
    }
  }, [activeRunId]);

  // If activeRunId is not set, select the first available case
  useEffect(() => {
    if (!activeRunId && cases && cases.length > 0) {
      api.startInvestigation(cases[0].id)
        .then(inv => {
          setActiveRunId(inv.id);
          if (onSelectRun) onSelectRun(inv.id);
        })
        .catch(() => undefined);
    }
  }, [activeRunId, cases, onSelectRun]);

  const updateOfficerField = (key: keyof Officer, val: string) => {
    const next = { ...officer, [key]: val };
    setOfficer(next);
    saveOfficer(next);
  };

  const handleGenerateCourtReport = async () => {
    if (!activeRunId) {
      setError('Please start or select an investigation case first.');
      return;
    }
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      const doc = await api.createCourtReport(activeRunId, {
        officer,
        courtName,
        notes,
      });
      setDocuments(prev => [doc, ...prev]);
      setSuccess(`Court Report PDF generated successfully: ${doc.title} (SHA-256: ${doc.sha256.slice(0, 16)}...)`);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const courtReports = documents.filter(d => d.kind === 'court_report');
  const otherDocs = documents.filter(d => d.kind !== 'court_report');

  return (
    <div className="space-y-5">
      <Panel title="JUDICIAL COURT DOSSIER & SECTION 63 BSA CERTIFICATE">
        <div className="space-y-4">
          <div className="border-l-4 border-teal-500 bg-slate-900/90 p-4">
            <h3 className="text-base font-bold text-slate-100 mb-1">
              Statutory Court Evidence Dossier (Bharatiya Sakshya Adhiniyam, 2023)
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Generates a comprehensive, court-admissible PDF document containing forensic fund-flow vector diagrams,
              complete on-chain transaction ledgers, SHA-256 evidence chain of custody, system audit logs, and a
              legally compliant <strong>Section 63 BSA Certificate (Part A & Part B)</strong> with officer signatures and official seals.
            </p>
          </div>

          {error && (
            <div className="border border-red-800 bg-red-950/40 p-3 font-mono text-xs text-red-300">
              {error}
            </div>
          )}

          {success && (
            <div className="border border-emerald-800 bg-emerald-950/40 p-3 font-mono text-xs text-emerald-300">
              {success}
            </div>
          )}

          {/* Configuration and Officer Details */}
          <div className="border border-slate-800 bg-slate-900/50 p-4 rounded">
            <div className="flex justify-between items-center mb-3">
              <span className="font-mono text-xs font-bold text-teal-400 uppercase tracking-wider">
                Court & Investigating Officer Particulars
              </span>
              <button 
                onClick={() => setShowConfig(!showConfig)}
                className="text-xs font-mono text-cyan-400 hover:text-cyan-200 underline"
              >
                {showConfig ? 'Hide Officer Settings' : 'Edit Officer & Court Details'}
              </button>
            </div>

            {showConfig && (
              <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-slate-800">
                <label className="block">
                  <span className="font-mono text-xs text-slate-400">Hon'ble Court Title</span>
                  <input
                    className="mt-1 block w-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                    value={courtName}
                    onChange={e => setCourtName(e.target.value)}
                    placeholder="Hon'ble Special Court for Cyber Crime"
                  />
                </label>
                <label className="block">
                  <span className="font-mono text-xs text-slate-400">Investigating Officer Name</span>
                  <input
                    className="mt-1 block w-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                    value={officer.name ?? ''}
                    onChange={e => updateOfficerField('name', e.target.value)}
                    placeholder="e.g. Insp. Vikram Singh"
                  />
                </label>
                <label className="block">
                  <span className="font-mono text-xs text-slate-400">Officer Rank / Designation</span>
                  <input
                    className="mt-1 block w-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                    value={officer.rank ?? ''}
                    onChange={e => updateOfficerField('rank', e.target.value)}
                    placeholder="e.g. Inspector of Police / Cyber Forensics Examiner"
                  />
                </label>
                <label className="block">
                  <span className="font-mono text-xs text-slate-400">Police Station / Forensic Unit</span>
                  <input
                    className="mt-1 block w-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                    value={officer.unit ?? ''}
                    onChange={e => updateOfficerField('unit', e.target.value)}
                    placeholder="e.g. Special Cyber Crime Investigation Cell & Forensic Lab"
                  />
                </label>
                <label className="block sm:col-span-2">
                  <span className="font-mono text-xs text-slate-400">Investigator Remarks / Notes (appended to Court Report)</span>
                  <textarea
                    rows={2}
                    className="mt-1 block w-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                    placeholder="Enter any specific case observations, seizure details, or notes to the Hon'ble Court..."
                  />
                </label>
              </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                disabled={busy || !activeRunId}
                onClick={handleGenerateCourtReport}
                className="border border-teal-500 bg-teal-900/60 px-5 py-2.5 font-mono text-xs font-bold tracking-wider text-teal-100 hover:bg-teal-800 disabled:opacity-40 transition-colors shadow flex items-center gap-2"
              >
                {busy ? (
                  <>
                    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-teal-200 border-t-transparent"></span>
                    GENERATING COURT DOSSIER (PDF)...
                  </>
                ) : (
                  <>⚡ GENERATE OFFICIAL COURT REPORT (SECTION 63 BSA PDF)</>
                )}
              </button>

              <span className="font-mono text-xs text-slate-400">
                Run ID: <span className="text-cyan-300 font-bold">{activeRunId ?? 'None Selected'}</span>
              </span>
            </div>
          </div>

          {/* List of Court Reports */}
          <div className="space-y-3 mt-6">
            <h3 className="font-mono text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
              <span>Generated Court Reports ({courtReports.length})</span>
              <button 
                onClick={() => loadDocuments()} 
                className="text-xs text-cyan-400 hover:text-cyan-200 font-mono"
              >
                REFRESH LIST
              </button>
            </h3>

            {courtReports.length === 0 ? (
              <div className="border border-slate-800 bg-slate-900/30 p-6 text-center text-xs text-slate-400">
                No court reports generated yet for this investigation run. Click "Generate Official Court Report" above.
              </div>
            ) : (
              <div className="space-y-3">
                {courtReports.map(doc => {
                  const filename = `${doc.title.replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`;
                  const formattedSize = (doc.sizeBytes / 1024).toFixed(1) + ' KB';
                  return (
                    <div key={doc.id} className="border border-slate-700 bg-slate-900/60 p-4 rounded shadow-sm hover:border-cyan-700/60 transition-colors space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono text-xs font-bold text-cyan-200">{doc.title}</span>
                          <StatusChip status={doc.status} />
                          <span className="border border-teal-800/80 bg-teal-950/40 text-teal-300 px-2 py-0.5 font-mono text-[10px] font-semibold">
                            SEC 63 BSA CERTIFIED
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openPdf(doc.id, false, filename).catch(e => setError(apiErrorMessage(e)))}
                            className="border border-cyan-700 bg-cyan-950/40 hover:bg-cyan-900 px-3 py-1 font-mono text-xs text-cyan-200 font-semibold transition-colors"
                          >
                            PREVIEW PDF
                          </button>
                          <button
                            onClick={() => openPdf(doc.id, true, filename).catch(e => setError(apiErrorMessage(e)))}
                            className="border border-slate-600 bg-slate-800 hover:bg-slate-700 px-3 py-1 font-mono text-xs text-slate-200 font-semibold transition-colors"
                          >
                            DOWNLOAD PDF
                          </button>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-1">
                        <span>Created: <span className="text-slate-200">{doc.createdAt ?? '-'}</span></span>
                        <span>Size: <span className="text-slate-200">{formattedSize}</span></span>
                        <span>Generated by: <span className="text-slate-200">{doc.createdBy}</span></span>
                      </div>

                      <div className="break-all font-mono text-xs text-slate-400 bg-slate-950/80 p-2 border border-slate-800 rounded">
                        <span className="text-teal-400 font-semibold">SHA-256: </span>
                        {doc.sha256}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* VASP Notices & Other Documents */}
          {otherDocs.length > 0 && (
            <div className="space-y-3 mt-6 pt-4 border-t border-slate-800">
              <h3 className="font-mono text-xs font-bold text-slate-400 uppercase tracking-wider">
                VASP Notices & Requisition Orders ({otherDocs.length})
              </h3>
              <div className="space-y-2">
                {otherDocs.map(doc => (
                  <div key={doc.id} className="border border-slate-800 bg-slate-900/40 p-3 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="font-mono text-xs font-semibold text-slate-200">{doc.title}</span>
                      <div className="text-[11px] font-mono text-slate-400">SHA-256: {doc.sha256.slice(0, 24)}...</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openPdf(doc.id, false).catch(e => setError(apiErrorMessage(e)))}
                        className="border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-xs text-slate-300 hover:text-cyan-300"
                      >
                        VIEW
                      </button>
                      <button
                        onClick={() => openPdf(doc.id, true).catch(e => setError(apiErrorMessage(e)))}
                        className="border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-xs text-slate-300 hover:text-cyan-300"
                      >
                        DOWNLOAD
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Panel>

      {/* Standard Replay Reports */}
      <Panel title="REPLAY & RAW DATA EXPORT">
        <p className="text-xs text-slate-300 mb-3">
          Export raw investigation datasets and view deterministic HTML case summaries for data verification:
        </p>
        <div className="flex flex-wrap gap-3 mb-4">
          <button 
            className="border border-teal-700 bg-teal-950/40 px-4 py-2 text-xs font-mono font-bold text-teal-300 hover:bg-teal-900/50 transition-colors" 
            onClick={() => activeRunId && api.reports(activeRunId).then(setItems)}
          >
            LOAD JSON REPORT
          </button>
          <button 
            className="border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-mono font-bold text-slate-200 hover:bg-slate-700 transition-colors" 
            onClick={() => window.open('http://localhost:8000/api/v1/reports/REPORT-CYBER-2026-001/html')}
          >
            OPEN HTML REPORT
          </button>
          <button 
            className="border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-mono font-bold text-slate-200 hover:bg-slate-700 transition-colors" 
            onClick={() => {
              const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' });
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = 'vaultx-investigation-report.json';
              a.click();
            }}
          >
            DOWNLOAD JSON
          </button>
        </div>
        {items.length > 0 && (
          <pre className="border border-slate-800 bg-slate-900 p-4 text-xs font-mono text-slate-300 overflow-auto max-h-96">
            {JSON.stringify(items, null, 2)}
          </pre>
        )}
      </Panel>
    </div>
  );
}

function Sahyog({ attributionId }: { attributionId: string }) {
  const { user } = useAuth();
  const [reply, setReply] = useState<Record<string, unknown> | null>(null);
  return (
    <Panel title="SAHYOG: LAW ENFORCEMENT INTEGRATION (MOCK)">
      <div className="mb-4 border-l-4 border-amber-500 bg-amber-950/30 p-3.5 text-sm text-amber-200">
        <strong className="font-mono text-xs uppercase tracking-wider block mb-1">MOCK MODE ACTIVE:</strong>
        Data is not submitted to any live government production system. SAHYOG protocol integration is simulated for demonstration.
      </div>
      <div className="flex gap-3">
        <button className="border border-teal-500 bg-teal-950/60 px-4 py-2.5 text-xs font-mono font-bold text-teal-300 hover:bg-teal-900/60 transition-colors shadow" onClick={() => api.prepareSahyog(attributionId).then(setReply)}>
          PREPARE MOCK SUBMISSION
        </button>
        {user?.role === 'Supervisor' && (
          <button className="border border-amber-500 bg-amber-950/60 px-4 py-2.5 text-xs font-mono font-bold text-amber-300 hover:bg-amber-900/60 transition-colors shadow" onClick={() => api.approveSahyog(attributionId).then(setReply)}>
            SUPERVISOR APPROVE
          </button>
        )}
      </div>
      {reply && (
        <div className="mt-4">
          <h3 className="font-mono text-xs text-slate-400 mb-2 uppercase font-semibold">Mock Response Payload</h3>
          <pre className="border border-slate-800 bg-slate-900 p-4 text-xs font-mono text-emerald-400 overflow-auto">
            {JSON.stringify(reply, null, 2)}
          </pre>
        </div>
      )}
    </Panel>
  );
}
