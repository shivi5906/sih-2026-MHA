'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/70 p-4">
    <h2 className="mb-3 font-mono text-xs tracking-wider text-teal-400">{title}</h2>
    {children}
  </section>
);

export function AuditLog() {
  const { user } = useAuth();
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const load = () => {
    setLoading(true);
    setError('');
    api.audit()
      .then(setItems)
      .catch(err => setError(String(err).includes('403') 
        ? 'Audit access requires an Auditor or Supervisor login.' 
        : 'Unable to load the audit log.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    void load();
  }, []);

  const paginatedItems = items.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(items.length / pageSize);

  return (
    <Panel title="AUDIT LOG">
      <div className="mb-3 flex items-center justify-between border border-slate-700 bg-slate-900 p-3 text-xs">
        <span>Current role: <b className="text-cyan-200">{user?.role || 'Unknown'}</b></span>
        <button 
          className="border border-cyan-500 px-3 py-1 font-mono text-[10px] text-cyan-100 hover:bg-cyan-950 transition-colors" 
          onClick={load}
        >
          REFRESH
        </button>
      </div>

      {error ? (
        <div className="border border-amber-600 bg-amber-950/30 p-3 text-xs text-amber-100">{error}</div>
      ) : loading ? (
        <div className="flex justify-center p-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <p className="text-xs text-slate-400 p-4 text-center">No audit events recorded.</p>
      ) : (
        <div className="space-y-3">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-700 font-mono text-[10px] text-cyan-300 bg-slate-900/50">
                <tr>
                  <th className="p-2">TIME</th>
                  <th className="p-2">ACTOR</th>
                  <th className="p-2">ACTION</th>
                  <th className="p-2">RESOURCE</th>
                  <th className="p-2">RESULT</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map(x => (
                  <tr key={String(x.id)} className="border-b border-slate-800/50 text-slate-200 hover:bg-slate-800/30">
                    <td className="p-2 whitespace-nowrap text-slate-400 font-mono text-[10px]">
                      {x.occurredAt ? new Date(String(x.occurredAt)).toLocaleString() : '—'}
                    </td>
                    <td className="p-2">{String(x.who)}</td>
                    <td className="p-2 text-cyan-200 font-mono text-[10px]">{String(x.what)}</td>
                    <td className="p-2 font-mono text-[10px] text-slate-300">{String(x.resource)}</td>
                    <td className="p-2">
                      <span className={`px-1.5 py-0.5 rounded-sm ${String(x.result).toLowerCase() === 'success' ? 'bg-emerald-950/50 text-emerald-300' : 'bg-amber-950/50 text-amber-300'}`}>
                        {String(x.result)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-800 pt-3">
              <button 
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
                className="border border-slate-700 px-3 py-1 font-mono text-[10px] text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                PREV
              </button>
              <span className="font-mono text-[10px] text-slate-400">
                PAGE {page + 1} OF {totalPages}
              </span>
              <button 
                disabled={page === totalPages - 1}
                onClick={() => setPage(p => p + 1)}
                className="border border-slate-700 px-3 py-1 font-mono text-[10px] text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                NEXT
              </button>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
