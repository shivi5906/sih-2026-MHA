'use client';

import { Attribution } from '@/lib/api';

interface AttributionPanelProps {
  items: Attribution[];
}

export function AttributionPanel({ items }: AttributionPanelProps) {
  const top = items[0];

  if (!top) {
    return (
      <div className="pt-4 text-center">
        <p className="text-xs text-slate-500">No attribution data available for this node.</p>
      </div>
    );
  }

  const getBandColor = (band: string) => {
    switch (band) {
      case 'HIGH': return 'border-emerald-500/50 bg-emerald-950/30 text-emerald-400';
      case 'MEDIUM': return 'border-amber-500/50 bg-amber-950/30 text-amber-400';
      case 'LOW': return 'border-red-500/50 bg-red-950/30 text-red-400';
      default: return 'border-slate-500/50 bg-slate-900/30 text-slate-400';
    }
  };

  const getScoreColorHex = (band: string) => {
    switch (band) {
      case 'HIGH': return '#10b981'; // emerald-500
      case 'MEDIUM': return '#f59e0b'; // amber-500
      case 'LOW': return '#ef4444'; // red-500
      default: return '#64748b'; // slate-500
    }
  };

  const scoreColor = getScoreColorHex(top.band);
  // Circle math
  const radius = 24;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (top.score * circumference);

  return (
    <div className="space-y-4 pt-4">
      <div className="flex items-start gap-4">
        {/* Radial score indicator */}
        <div className="relative h-16 w-16 shrink-0">
          <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 64 64">
            <circle
              cx="32" cy="32" r="24"
              className="fill-none stroke-slate-800" strokeWidth="4"
            />
            <circle
              cx="32" cy="32" r="24"
              className="fill-none transition-all duration-1000 ease-out"
              stroke={scoreColor}
              strokeWidth="4"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center font-mono text-sm font-bold text-slate-200">
            {Number(top.score).toFixed(2)}
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="font-sans text-lg font-bold text-cyan-50">{top.hypothesis}</h3>
          <div className="flex flex-wrap gap-2">
            <span className={`px-2 py-0.5 border font-mono text-[10px] uppercase ${getBandColor(top.band)}`}>
              {top.band} CONFIDENCE
            </span>
            <span className="border border-amber-800 px-2 py-0.5 font-mono text-[10px] text-amber-300">
              UNCALIBRATED
            </span>
          </div>
          <p className="text-xs text-slate-400">
            {top.epistemicLabel === 'NO_ATTRIBUTION' ? 'ABSTAINED: no attribution.' : `Epistemic status: ${top.epistemicLabel}`}
          </p>
        </div>
      </div>

      <details className="group border border-slate-800 bg-slate-900/50">
        <summary className="cursor-pointer list-none border-b border-slate-800 bg-slate-900/80 p-2 font-mono text-[10px] text-teal-400 hover:bg-slate-800">
          <div className="flex items-center justify-between">
            <span>WHY THIS VASP?</span>
            <span className="text-slate-500 group-open:rotate-180 transition-transform">▼</span>
          </div>
        </summary>
        <div className="p-3 text-xs space-y-2">
          {top.supporting.length > 0 ? (
            top.supporting.map((id, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-teal-500">▶</span>
                <span className="text-slate-300">
                  <span className="font-mono text-teal-400">{id}</span> · OBSERVED / ATTRIBUTED
                </span>
              </div>
            ))
          ) : (
            <p className="text-slate-500">No supporting evidence provided.</p>
          )}
        </div>
      </details>

      <div className="grid gap-3 border-t border-slate-800 pt-3 text-xs">
        <div>
          <span className="font-mono text-[10px] text-slate-500 block mb-1">ALTERNATIVES</span>
          <p className="text-slate-300">{items.slice(1).map(x => x.hypothesis).join(', ') || 'None identified'}</p>
        </div>
        
        {top.contradicting.length > 0 && (
          <div>
            <span className="font-mono text-[10px] text-amber-500 block mb-1">CONTRADICTING EVIDENCE</span>
            <ul className="list-disc pl-4 text-slate-300">
              {top.contradicting.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}
        
        <div>
          <span className="font-mono text-[10px] text-cyan-500 block mb-1">EVIDENCE GAPS / NEXT ACTIONS</span>
          <p className="text-slate-300">{top.nextActions.join(' ') || 'Additional independent source required.'}</p>
        </div>
      </div>
    </div>
  );
}
