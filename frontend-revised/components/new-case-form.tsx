'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/70 p-4">
    <h2 className="mb-3 font-mono text-xs tracking-wider text-teal-400">{title}</h2>
    {children}
  </section>
);

export function NewCaseForm({ onCreated }: { onCreated?: () => void }) {
  const [step, setStep] = useState(1);
  const [wallet, setWallet] = useState('');
  const [chain, setChain] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  
  const handleNext = () => {
    if (step === 1 && !wallet.trim()) {
      setError('Wallet address is required.');
      return;
    }
    setError('');
    
    if (step === 2) {
      setStep(3);
      startTrace();
    } else {
      setStep(step + 1);
    }
  };

  const startTrace = async () => {
    try {
      const caseResult = await api.createCase(
        `CASE-${Date.now()}`,
        title || `Trace ${wallet.slice(0, 12)}…`,
        wallet,
        chain || undefined
      );
      
      if (onCreated) onCreated();
      
      const inv = await api.startInvestigation(caseResult.id, wallet, chain || undefined);
      
      if (inv.status === 'failed') {
        setError(String(inv.error || 'Trace failed. Check the wallet address and try again.'));
        setStep(1); // Return to step 1 on error
        return;
      }
      
      window.dispatchEvent(new CustomEvent('vault-x:set-run', { detail: inv.id }));
      window.dispatchEvent(new CustomEvent('vault-x:navigate', { detail: 'detail' }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trace failed.');
      setStep(1);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <Panel title="NEW INVESTIGATION">
        {/* Stepper Header */}
        <div className="mb-8 flex items-center justify-between font-mono text-[10px]">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex flex-col items-center gap-2">
              <div className={`flex h-8 w-8 items-center justify-center rounded-full border-2 ${
                step > s ? 'border-teal-500 bg-teal-950 text-teal-300' :
                step === s ? 'border-cyan-400 bg-cyan-950 text-cyan-200' :
                'border-slate-700 bg-slate-900 text-slate-500'
              }`}>
                {step > s ? '✓' : s}
              </div>
              <span className={step >= s ? 'text-cyan-200' : 'text-slate-500'}>
                {s === 1 ? 'WALLET & CHAIN' : s === 2 ? 'CASE DETAILS' : 'TRACING'}
              </span>
            </div>
          ))}
          <div className="absolute left-1/2 top-8 -z-10 h-0.5 w-[calc(100%-8rem)] -translate-x-1/2 bg-slate-800" />
        </div>

        {error && (
          <div className="mb-4 border border-red-800 bg-red-950/30 p-3 font-mono text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Step 1: Wallet & Chain */}
        {step === 1 && (
          <div className="space-y-4">
            <label className="block font-mono text-[10px] text-cyan-200">
              SUSPECT WALLET ADDRESS <span className="text-amber-400">*</span>
              <input
                className="mt-1 block w-full border border-cyan-700 bg-slate-900 p-2.5 font-mono text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                value={wallet}
                onChange={(e) => setWallet(e.target.value)}
                placeholder="bc1q… / 0x… / T…"
              />
            </label>
            <label className="block font-mono text-[10px] text-cyan-200">
              CHAIN
              <select
                className="mt-1 block w-full border border-slate-700 bg-slate-900 p-2.5 font-sans text-sm text-white focus:border-cyan-400 focus:outline-none"
                value={chain}
                onChange={(e) => setChain(e.target.value)}
              >
                <option value="">Auto-detect</option>
                <option value="bitcoin">Bitcoin</option>
                <option value="ethereum">Ethereum</option>
                <option value="tron">Tron</option>
              </select>
            </label>
          </div>
        )}

        {/* Step 2: Case Details */}
        {step === 2 && (
          <div className="space-y-4">
            <label className="block font-mono text-[10px] text-cyan-200">
              CASE TITLE
              <input
                className="mt-1 block w-full border border-slate-700 bg-slate-900 p-2.5 font-sans text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Optional — auto-generated if blank"
              />
            </label>
            <label className="block font-mono text-[10px] text-cyan-200">
              DESCRIPTION
              <textarea
                className="mt-1 block w-full border border-slate-700 bg-slate-900 p-2.5 font-sans text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none min-h-[100px]"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional case notes or references..."
              />
            </label>
          </div>
        )}

        {/* Step 3: Tracing */}
        {step === 3 && (
          <div className="flex flex-col items-center gap-6 py-12">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-teal-400 border-t-transparent" />
            <div className="text-center">
              <p className="animate-pulse font-mono text-sm text-teal-300">TRACING BLOCKCHAIN…</p>
              <p className="mt-2 font-mono text-[10px] text-slate-400">
                Querying transactions • Building graph • Identifying exchanges
              </p>
            </div>
          </div>
        )}

        {/* Navigation */}
        {step < 3 && (
          <div className="mt-8 flex justify-end gap-3 border-t border-slate-800 pt-4">
            {step > 1 && (
              <button
                className="border border-slate-600 px-4 py-2 font-mono text-xs text-slate-300 hover:bg-slate-800"
                onClick={() => setStep(step - 1)}
              >
                BACK
              </button>
            )}
            <button
              className="border border-teal-600 bg-teal-950/50 px-6 py-2 font-mono text-xs font-bold tracking-wider text-teal-200 hover:bg-teal-900/60"
              onClick={handleNext}
            >
              {step === 1 ? 'NEXT' : 'START TRACE'}
            </button>
          </div>
        )}
      </Panel>
    </div>
  );
}
