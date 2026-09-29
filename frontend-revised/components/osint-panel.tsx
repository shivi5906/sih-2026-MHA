'use client';

import { useEffect, useState } from 'react';
import { api, ApiOfflineError, OsintChannel, OsintReport, OsintTarget } from '@/lib/api';
import { NoticeComposer } from './notice-composer';
import { ColumnChart, EmptyChart, fmt, HBarChart, pct, ScoreRing, ShareBar, shortAddr, StatTile } from './osint-charts';

const Section = ({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) => (
  <div className="border border-slate-800 bg-slate-900/40 p-3">
    <div className="mb-2 flex items-baseline justify-between gap-2">
      <h3 className="font-mono text-[10px] tracking-wider text-teal-400">{title}</h3>
      {hint && <span className="font-mono text-[9px] text-slate-500">{hint}</span>}
    </div>
    {children}
  </div>
);

const Chip = ({ children, tone }: { children: React.ReactNode; tone: 'emerald' | 'amber' | 'red' | 'slate' | 'cyan' }) => {
  const tones = {
    emerald: 'border-emerald-600/60 bg-emerald-950/40 text-emerald-300',
    amber: 'border-amber-600/60 bg-amber-950/40 text-amber-300',
    red: 'border-red-600/60 bg-red-950/40 text-red-300',
    slate: 'border-slate-600 bg-slate-900 text-slate-400',
    cyan: 'border-cyan-700 bg-cyan-950/40 text-cyan-300',
  };
  return <span className={`inline-block border px-1.5 py-0.5 font-mono text-[9px] uppercase ${tones[tone]}`}>{children}</span>;
};

const priorityTone = (p: string) => (p === 'HIGH' ? 'red' : p === 'MEDIUM' ? 'amber' : 'slate') as 'red' | 'amber' | 'slate';

const channelTone = (s: OsintChannel['status']) => (s === 'FOUND' ? 'emerald' : s === 'NOT_PUBLIC' ? 'amber' : 'slate') as 'emerald' | 'amber' | 'slate';

const channelStatus = (s: OsintChannel['status']) => (s === 'FOUND' ? 'Found' : s === 'NOT_PUBLIC' ? 'Lawful request' : 'Not found');

function TargetCard({ target, open, onToggle, onFocus }: { target: OsintTarget; open: boolean; onToggle: () => void; onFocus?: (address: string) => void }) {
  return (
    <div className={`border ${open ? 'border-cyan-700 bg-slate-900/70' : 'border-slate-800 bg-slate-900/30'} transition-colors`}>
      <button onClick={onToggle} className="flex w-full items-center gap-3 p-3 text-left hover:bg-slate-800/40">
        <ScoreRing value={target.attributionScore} label="Attribution score (UNCALIBRATED)" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-sans text-sm font-bold text-cyan-50">{target.vasp}</span>
            <Chip tone={priorityTone(target.priority)}>{target.priority} priority</Chip>
            <Chip tone="slate">{target.epistemicLabel}</Chip>
          </div>
          <div className="mt-1 truncate font-mono text-[10px] text-slate-400" title={target.targetAddress}>
            {target.chain ?? 'Unknown chain'} · {shortAddr(target.targetAddress)}
          </div>
          <div className="mt-1 font-mono text-[9px] text-slate-500">
            OSINT coverage {(target.osintCoverage * 100).toFixed(0)}% · priority index {target.investigationPriority.toFixed(2)} · UNCALIBRATED
          </div>
        </div>
        <span className={`font-mono text-[10px] text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-slate-800 p-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatTile label="Inbound txs" value={fmt(target.inflow.txCount, 0)} tone="slate" />
            <StatTile label="Inbound value" value={`${fmt(target.inflow.totalValue, 4)} ${target.inflow.asset ?? ''}`} tone="slate" />
            <StatTile label="Unique senders" value={fmt(target.inflow.uniqueSenders, 0)} tone="slate" />
            <StatTile label="Seen" value={target.inflow.firstSeen ?? '—'} sub={target.inflow.lastSeen && target.inflow.lastSeen !== target.inflow.firstSeen ? `to ${target.inflow.lastSeen}` : undefined} tone="slate" />
          </div>

          <div className="flex flex-wrap gap-2">
            {onFocus && (
              <button onClick={() => onFocus(target.targetAddress)} className="border border-cyan-700 bg-cyan-950/50 px-2 py-1 font-mono text-[10px] text-cyan-100 hover:bg-cyan-900">
                LOCATE IN GRAPH
              </button>
            )}
            {target.profile.website && (
              <a href={target.profile.website} target="_blank" rel="noopener noreferrer" className="border border-slate-600 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-200 hover:text-cyan-300">
                OFFICIAL SITE ↗
              </a>
            )}
            {target.profile.knownHotWallet && <Chip tone="cyan">Known hot wallet · OBSERVED</Chip>}
            {!target.profile.inRegistry && <Chip tone="amber">Not in VASP registry</Chip>}
          </div>
          {target.profile.note && <p className="text-[11px] text-amber-300/90">{target.profile.note}</p>}

          <Section title="PUBLIC CHANNELS (VASP)" hint="organisation-level, not the account holder">
            <div className="divide-y divide-slate-800">
              {target.channels.map(c => (
                <div key={c.platform} className="grid grid-cols-[88px_1fr_auto] items-center gap-2 py-1.5 text-[11px]" title={c.note}>
                  <span className="font-mono text-[10px] text-slate-400">{c.platform}</span>
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="truncate font-mono text-cyan-300 hover:underline">{c.handle} ↗</a>
                  ) : (
                    <span className="truncate text-slate-500">{c.status === 'NOT_PUBLIC' ? 'Not publicly listed' : 'No profile held'}</span>
                  )}
                  <span className="flex gap-1">
                    <Chip tone={channelTone(c.status)}>{channelStatus(c.status)}</Chip>
                    <Chip tone="slate">{c.epistemicLabel}</Chip>
                  </span>
                </div>
              ))}
            </div>
          </Section>

          <Section title="ACCOUNT HOLDER IDENTITY" hint={target.accountHolder.route}>
            <ul className="grid gap-1 sm:grid-cols-2">
              {target.accountHolder.fields.map(f => (
                <li key={f} className="flex items-center justify-between gap-2 border border-dashed border-slate-700 bg-slate-950/50 px-2 py-1.5 text-[11px]">
                  <span className="text-slate-300">{f}</span>
                  <span className="font-mono text-[9px] text-amber-400">PENDING</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[10px] text-slate-500">
              Held by the VASP under KYC. Available only through a lawful request routed via SAHYOG (MOCK in this prototype). Nothing here is inferred.
            </p>
          </Section>

          <Section title="OSINT PIVOTS" hint="opens public sources in a new tab">
            <div className="flex flex-wrap gap-1.5">
              {target.pivots.map(p => (
                <a key={p.url} href={p.url} target="_blank" rel="noopener noreferrer" className="border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-[10px] text-slate-300 hover:border-cyan-600 hover:text-cyan-300">
                  {p.name} ↗
                </a>
              ))}
            </div>
          </Section>

          <Section title="LIVE CONNECTORS" hint="MOCK: no live query performed">
            <div className="grid gap-1.5 sm:grid-cols-2">
              {target.connectors.map(c => (
                <div key={c.name} className="border border-slate-800 bg-slate-950/60 p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-slate-300">{c.name}</span>
                    <Chip tone="slate">Not connected</Chip>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">{c.purpose}</p>
                </div>
              ))}
            </div>
          </Section>

          {target.nextActions.length > 0 && (
            <Section title="NEXT ACTIONS">
              <ul className="list-disc space-y-0.5 pl-4 text-[11px] text-slate-300">
                {target.nextActions.map(a => <li key={a}>{a}</li>)}
              </ul>
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

function Intelligence({ report, onFocus }: { report: OsintReport; onFocus?: (address: string) => void }) {
  const [openId, setOpenId] = useState<string | null>(report.targets[0] ? `${report.targets[0].id}-${report.targets[0].targetAddress}` : null);
  const platforms = report.targets[0]?.channels.map(c => c.platform) ?? [];

  if (report.targets.length === 0) {
    return (
      <div className="border border-slate-700 bg-slate-900/40 p-4 text-center">
        <div className="font-mono text-xs text-amber-300">ABSTAINED: no named VASP attribution for this run</div>
        <p className="mt-2 text-[11px] text-slate-400">
          OSINT enrichment runs only on attributed VASPs. {report.summary.hypothesesConsidered} hypotheses were considered, and all were abstentions. The graph analytics tab is still available.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3 xl:grid-cols-2">
        <Section title="ATTRIBUTION SCORE BY VASP" hint="UNCALIBRATED">
          <HBarChart max={1} format={n => n.toFixed(2)} rows={report.targets.map(t => ({ label: t.vasp, value: t.attributionScore, highlight: t.priority === 'HIGH' }))} />
        </Section>
        <Section title="INVESTIGATION PRIORITY INDEX" hint="0.7 × score + 0.3 × coverage">
          <HBarChart max={1} color="#a78bfa" format={n => n.toFixed(2)} rows={report.targets.map(t => ({ label: t.vasp, value: t.investigationPriority }))} />
        </Section>
      </div>

      <Section title="CHANNEL COVERAGE MATRIX" hint="green = public profile held">
        <div className="overflow-x-auto">
          <table className="w-full font-mono text-[10px]">
            <thead>
              <tr className="text-slate-500">
                <th className="py-1 pr-2 text-left font-normal">VASP</th>
                {platforms.map(p => <th key={p} className="px-1 py-1 font-normal">{p.replace(' / Twitter', '')}</th>)}
              </tr>
            </thead>
            <tbody>
              {report.targets.map(t => (
                <tr key={`${t.id}-${t.targetAddress}`} className="border-t border-slate-800">
                  <td className="py-1.5 pr-2 text-slate-300">{t.vasp}</td>
                  {t.channels.map(c => (
                    <td key={c.platform} className="px-1 py-1.5 text-center" title={`${c.platform}: ${channelStatus(c.status)}`}>
                      <span className={`inline-block h-3 w-3 ${c.status === 'FOUND' ? 'bg-emerald-500' : c.status === 'NOT_PUBLIC' ? 'bg-amber-500/70' : 'bg-slate-700'}`} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div className="space-y-2">
        {report.targets.map(t => {
          const key = `${t.id}-${t.targetAddress}`;
          return <TargetCard key={key} target={t} open={openId === key} onToggle={() => setOpenId(openId === key ? null : key)} onFocus={onFocus} />;
        })}
      </div>
    </div>
  );
}

function Analytics({ report, onFocus }: { report: OsintReport; onFocus?: (address: string) => void }) {
  const g = report.graphAnalytics;
  const asset = g.asset ?? '';
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <StatTile label="Addresses" value={fmt(g.nodes, 0)} />
        <StatTile label="Transfers" value={fmt(g.edges, 0)} sub={`${fmt(g.uniqueLinks, 0)} unique links`} />
        <StatTile label="Total value" value={`${fmt(g.totalValue, 2)} ${asset}`} />
        <StatTile label="Components" value={fmt(g.components, 0)} tone="slate" sub="weakly connected" />
        <StatTile label="Density" value={g.density.toFixed(4)} tone="slate" />
        <StatTile label="Sources / sinks" value={`${fmt(g.sources, 0)} / ${fmt(g.sinks, 0)}`} tone="slate" />
      </div>

      <Section title="VALUE REACHING ATTRIBUTED VASPS" hint="OBSERVED flow, attribution UNCALIBRATED">
        <ShareBar share={g.valueIntoVaspsShare} label={`${fmt(g.valueIntoVasps, 4)} ${asset} of ${fmt(g.totalValue, 2)} ${asset}`} />
      </Section>

      <div className="grid gap-3 xl:grid-cols-2">
        <Section title="TOP HUBS BY DEGREE" hint="click to locate">
          {g.topHubs.length === 0 ? <EmptyChart /> : (
            <div className="space-y-1">
              {g.topHubs.map(h => (
                <button key={h.address} onClick={() => onFocus?.(h.address)} className="grid w-full grid-cols-[1fr_auto] items-center gap-2 border border-transparent px-1 py-0.5 text-left font-mono text-[10px] hover:border-slate-700 hover:bg-slate-800/50" title={h.address}>
                  <span className={`truncate ${h.isVasp ? 'text-yellow-300' : 'text-slate-300'}`}>{h.address.startsWith('virtual:') ? h.address : shortAddr(h.address)}</span>
                  <span className="text-slate-400">in {h.inDegree} · out {h.outDegree}</span>
                </button>
              ))}
            </div>
          )}
        </Section>
        <Section title="TRANSFER SIZE DISTRIBUTION" hint={asset}>
          <ColumnChart rows={g.valueBuckets.map(b => ({ label: b.label, value: b.count }))} />
        </Section>
      </div>

      <Section title="ACTIVITY TIMELINE" hint="transfers per month">
        <ColumnChart color="#38bdf8" rows={g.timeline.map(t => ({ label: t.month, value: t.count }))} />
      </Section>

      <div className="grid gap-3 xl:grid-cols-2">
        <Section title="TRANSFERS BY SOURCE DATASET">
          <HBarChart color="#2dd4bf" format={n => fmt(n, 0)} rows={g.datasets.map(d => ({ label: d.name, value: d.count }))} />
        </Section>
        <Section title="HOP DEPTH DISTRIBUTION">
          {g.hopDistribution.length === 0
            ? <EmptyChart text="Hop depth is recorded only for live traces." />
            : <ColumnChart color="#f472b6" rows={g.hopDistribution.map(h => ({ label: `hop ${h.hop}`, value: h.count }))} />}
        </Section>
      </div>
    </div>
  );
}

export function OsintPanel({ runId, onFocusAddress }: { runId?: string; onFocusAddress?: (address: string) => void }) {
  const [report, setReport] = useState<OsintReport | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<'intel' | 'analytics' | 'notices'>('intel');

  const load = () => {
    if (!runId) return;
    setLoading(true);
    setError('');
    api.osint(runId)
      .then(setReport)
      .catch(e => setError(e instanceof ApiOfflineError ? 'API offline. Start the backend to run OSINT enrichment.' : 'Unable to load OSINT enrichment for this run.'))
      .finally(() => setLoading(false));
  };

  useEffect(load, [runId]);

  if (!runId) {
    return <EmptyChart text="Open a case investigation to run OSINT enrichment." />;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <Chip tone="cyan">{report?.banner ?? 'SNAPSHOT / CASE REPLAY'}</Chip>
        <Chip tone="amber">UNCALIBRATED</Chip>
        <Chip tone="slate">Connectors: MOCK</Chip>
        <Chip tone="slate">SAHYOG: MOCK</Chip>
        <button onClick={load} disabled={loading} className="ml-auto border border-slate-600 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-200 hover:text-cyan-300 disabled:opacity-50">
          {loading ? 'RUNNING…' : 'RE-RUN'}
        </button>
      </div>

      {error && <div className="border border-red-800 bg-red-950/30 p-3 font-mono text-xs text-red-300">{error}</div>}

      {loading && !report && (
        <div className="space-y-2">
          {[0, 1, 2].map(i => <div key={i} className="h-16 animate-pulse border border-slate-800 bg-slate-900/60" />)}
        </div>
      )}

      {report && (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatTile label="VASP targets" value={String(report.summary.targets)} sub={`${report.summary.hypothesesConsidered} hypotheses read`} />
            <StatTile label="High priority" value={String(report.summary.highPriority)} tone={report.summary.highPriority > 0 ? 'red' : 'slate'} />
            <StatTile label="Channels found" value={`${report.summary.channelsFound} / ${report.summary.channelsChecked}`} tone="emerald" />
            <StatTile label="Value to VASPs" value={pct(report.graphAnalytics.valueIntoVaspsShare)} tone="amber" sub="of traced value" />
          </div>

          <div className="flex gap-1 border-b border-slate-800 pb-2">
            {([['intel', 'INTELLIGENCE'], ['analytics', 'GRAPH ANALYTICS'], ['notices', 'NOTICES TO VASP']] as const).map(([key, name]) => (
              <button key={key} onClick={() => setView(key)}
                className={`px-2 py-1 font-mono text-[10px] transition-colors ${view === key ? 'border-b-2 border-teal-500 bg-teal-950/50 font-bold text-teal-300' : 'text-slate-500 hover:text-slate-300'}`}>
                {name}
              </button>
            ))}
          </div>

          {view === 'intel' && <Intelligence key={report.generatedAt} report={report} onFocus={onFocusAddress} />}
          {view === 'analytics' && <Analytics report={report} onFocus={onFocusAddress} />}
          {view === 'notices' && <NoticeComposer runId={runId} />}

          <p className="border-t border-slate-800 pt-2 text-[10px] leading-relaxed text-slate-500">{report.disclaimer}</p>
        </>
      )}
    </div>
  );
}
