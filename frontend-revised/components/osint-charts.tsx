'use client';

// Dependency-free SVG/CSS charts for the OSINT panel.

// Small amounts keep 4 significant digits so they never round to 0.
export const fmt = (n: number, digits = 2) => {
  if (!Number.isFinite(n)) return '—';
  if (n !== 0 && Math.abs(n) < 1) return n.toLocaleString(undefined, { maximumSignificantDigits: 4 });
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
};

export const pct = (share: number) => {
  const p = (Number(share) || 0) * 100;
  return p > 0 && p < 0.1 ? '<0.1%' : `${p.toFixed(1)}%`;
};

export const shortAddr =(a: string) => (a.length > 18 ? `${a.slice(0, 8)}…${a.slice(-6)}` : a);

export function StatTile({ label, value, sub, tone = 'cyan' }: { label: string; value: string; sub?: string; tone?: 'cyan' | 'amber' | 'emerald' | 'red' | 'slate' }) {
  const tones = {
    cyan: 'border-cyan-800 bg-cyan-950/30 text-cyan-100',
    amber: 'border-amber-700 bg-amber-950/30 text-amber-200',
    emerald: 'border-emerald-800 bg-emerald-950/30 text-emerald-200',
    red: 'border-red-800 bg-red-950/30 text-red-200',
    slate: 'border-slate-700 bg-slate-900/50 text-slate-200',
  };
  return (
    <div className={`border p-2 font-mono ${tones[tone]}`}>
      <div className="text-[9px] uppercase tracking-wider opacity-80">{label}</div>
      <div className="mt-1 text-base font-bold leading-tight">{value}</div>
      {sub && <div className="mt-0.5 text-[9px] opacity-70">{sub}</div>}
    </div>
  );
}

export function ScoreRing({ value, size = 56, label }: { value: number; size?: number; label?: string }) {
  const v = Math.max(0, Math.min(1, Number(value) || 0));
  const r = size / 2 - 5;
  const c = 2 * Math.PI * r;
  const color = v >= 0.85 ? '#10b981' : v >= 0.5 ? '#f59e0b' : '#ef4444';
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} title={label}>
      <svg className="h-full w-full -rotate-90" viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e293b" strokeWidth="4" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - v * c} className="transition-all duration-700" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center font-mono text-xs font-bold text-slate-100">{v.toFixed(2)}</div>
    </div>
  );
}

export function HBarChart({ rows, color = '#22d3ee', format = (n: number) => fmt(n), max }: {
  rows: Array<{ label: string; value: number; highlight?: boolean; title?: string }>;
  color?: string; format?: (n: number) => string; max?: number;
}) {
  if (rows.length === 0) return <EmptyChart />;
  const top = max ?? Math.max(...rows.map(r => r.value), 0);
  return (
    <div className="space-y-1.5">
      {rows.map((r, i) => (
        <div key={`${r.label}-${i}`} className="grid grid-cols-[110px_1fr_56px] items-center gap-2 font-mono text-[10px]" title={r.title ?? r.label}>
          <span className={`truncate ${r.highlight ? 'text-yellow-300' : 'text-slate-400'}`}>{r.label}</span>
          <div className="h-2.5 bg-slate-800/80">
            <div className="h-full transition-all duration-700" style={{ width: `${top > 0 ? Math.max(2, (r.value / top) * 100) : 0}%`, background: r.highlight ? '#facc15' : color }} />
          </div>
          <span className="text-right text-slate-200">{format(r.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function ColumnChart({ rows, color = '#2dd4bf', height = 110, format = (n: number) => fmt(n, 0) }: {
  rows: Array<{ label: string; value: number }>; color?: string; height?: number; format?: (n: number) => string;
}) {
  if (rows.length === 0 || rows.every(r => r.value === 0)) return <EmptyChart />;
  const top = Math.max(...rows.map(r => r.value));
  const every = Math.ceil(rows.length / 8);
  return (
    <div>
      <div className="flex items-end gap-[3px] border-b border-l border-slate-700 px-1" style={{ height }}>
        {rows.map((r, i) => (
          <div key={`${r.label}-${i}`} className="group relative flex h-full flex-1 items-end" title={`${r.label}: ${format(r.value)}`}>
            <div className="w-full transition-all duration-700 group-hover:brightness-125" style={{ height: `${top > 0 ? Math.max(r.value > 0 ? 3 : 0, (r.value / top) * 100) : 0}%`, background: color }} />
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-[3px] px-1 font-mono text-[8px] text-slate-500">
        {rows.map((r, i) => (
          <span key={`${r.label}-l-${i}`} className="flex-1 truncate text-center">{i % every === 0 ? r.label : ''}</span>
        ))}
      </div>
    </div>
  );
}

export function ShareBar({ share, label }: { share: number; label: string }) {
  const width = Math.max(0, Math.min(1, share)) * 100;
  return (
    <div className="font-mono text-[10px]">
      <div className="mb-1 flex justify-between text-slate-400"><span>{label}</span><span className="text-yellow-300">{pct(share)}</span></div>
      <div className="flex h-3 overflow-hidden bg-slate-800">
        <div className="bg-yellow-400 transition-all duration-700" style={{ width: `${width > 0 ? Math.max(width, 0.5) : 0}%` }} />
      </div>
    </div>
  );
}

export function EmptyChart({ text = 'No data recorded for this run.' }: { text?: string }) {
  return <div className="flex h-20 items-center justify-center border border-dashed border-slate-700 font-mono text-[10px] text-slate-500">{text}</div>;
}
