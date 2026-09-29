'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/70 p-4">
    <h2 className="mb-3 font-mono text-xs tracking-wider text-teal-400">{title}</h2>
    {children}
  </section>
);

export function EvidenceRegister() {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [results, setResults] = useState<Record<string, { valid: boolean; message: string }>>({});
  const [chainValid, setChainValid] = useState<boolean | null>(null);

  useEffect(() => {
    api.evidence().then(setRows).catch(console.error);
  }, []);

  const verifyRow = async (id: string) => {
    try {
      const r = await api.verifyEvidence(id);
      setResults(prev => ({
        ...prev,
        [id]: { valid: r.valid, message: r.valid ? 'OK' : `Broken at ${r.firstBrokenLink}` }
      }));
      // Update overall chain status based on this check (simplistic)
      if (chainValid !== false) {
        setChainValid(r.valid);
      }
    } catch (e) {
      setResults(prev => ({ ...prev, [id]: { valid: false, message: 'Error verifying' } }));
      setChainValid(false);
    }
  };

  return (
    <Panel title="EVIDENCE REGISTER">
      <div className="mb-4 flex items-center justify-between border border-slate-800 bg-slate-900/50 p-3">
        <div className="font-mono text-xs">
          <span className="text-slate-400">Chain integrity: </span>
          {chainValid === null ? (
            <span className="text-slate-300">UNVERIFIED</span>
          ) : chainValid ? (
            <span className="text-emerald-400">VALID</span>
          ) : (
            <span className="text-red-400">BROKEN</span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-700 font-mono text-[10px] text-cyan-300">
            <tr>
              <th className="p-2 cursor-pointer hover:text-cyan-100">ID</th>
              <th className="p-2 cursor-pointer hover:text-cyan-100">TYPE</th>
              <th className="p-2 cursor-pointer hover:text-cyan-100">SOURCE TIER</th>
              <th className="p-2">DESCRIPTION</th>
              <th className="p-2">INTEGRITY HASH</th>
              <th className="p-2 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => {
              const id = String(row.id);
              const result = results[id];
              return (
                <tr key={id} className="border-b border-slate-800 text-slate-200 hover:bg-slate-800/30">
                  <td className="p-2 font-mono text-teal-400 whitespace-nowrap">{id}</td>
                  <td className="p-2">{String(row.type)}</td>
                  <td className="p-2">
                    <span className="px-1.5 py-0.5 border border-slate-700 bg-slate-800">
                      {String(row.sourceTier || 'C')}
                    </span>
                  </td>
                  <td className="p-2">{String(row.description || '—')}</td>
                  <td className="p-2 font-mono text-[10px] text-slate-500">
                    {String(row.hash || '').slice(0, 16)}...
                  </td>
                  <td className="p-2 text-right">
                    {result ? (
                      <span className={`font-mono text-[10px] ${result.valid ? 'text-emerald-400' : 'text-red-400'}`}>
                        {result.valid ? '✓ VALID' : `✗ ${result.message}`}
                      </span>
                    ) : (
                      <button 
                        className="border border-teal-800 px-2 py-1 text-[10px] text-teal-400 hover:bg-teal-950" 
                        onClick={() => verifyRow(id)}
                      >
                        VERIFY
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-slate-500">No evidence items registered.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
