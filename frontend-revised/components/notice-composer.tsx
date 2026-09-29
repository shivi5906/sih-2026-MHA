'use client';

import { useEffect, useState } from 'react';
import { api, apiErrorMessage, DocumentSummary, EmailStatus, fetchPdfUrl, NoticeDraft, Officer } from '@/lib/api';
import { shortAddr } from './osint-charts';

const OFFICER_KEY = 'vault-x-officer';

function loadOfficer(): Officer {
  try { return JSON.parse(window.localStorage.getItem(OFFICER_KEY) || '{}'); } catch { return {}; }
}

function saveOfficer(officer: Officer) {
  try { window.localStorage.setItem(OFFICER_KEY, JSON.stringify(officer)); } catch { /* storage unavailable */ }
}

const inputCls = 'mt-1 block w-full border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none';
const labelCls = 'font-mono text-xs uppercase tracking-wider text-slate-300 font-semibold';

export async function openPdf(documentId: string, download = false, filename = 'document.pdf') {
  const url = await fetchPdfUrl(`/documents/${documentId}/pdf`);
  if (download) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  } else {
    window.open(url, '_blank', 'noopener');
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function StatusChip({ status }: { status: string }) {
  const tone = status === 'SENT' ? 'border-emerald-600 text-emerald-300 bg-emerald-950/40'
    : status === 'SUBMITTED' ? 'border-cyan-600 text-cyan-300 bg-cyan-950/40'
    : status === 'QUEUED_OUTBOX' ? 'border-amber-600 text-amber-300 bg-amber-950/40'
    : 'border-slate-600 text-slate-300 bg-slate-900';
  return <span className={`border px-2 py-0.5 font-mono text-xs font-medium ${tone}`}>{status.replace('_', ' ')}</span>;
}

function DocumentCard({ doc, email, onSent }: { doc: DocumentSummary; email: EmailStatus | null; onSent: (d: DocumentSummary) => void }) {
  const [channel, setChannel] = useState<'email' | 'sahyog'>('email');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const recipient = String(doc.meta.recipientEmail ?? '');
  const deliveries = (doc.meta.deliveries ?? []) as Array<Record<string, any>>;
  const last = deliveries[deliveries.length - 1];
  const filename = `${String(doc.meta.noticeNumber ?? doc.id).replace(/\//g, '-')}.pdf`;

  const send = async () => {
    setBusy(true);
    setError('');
    try {
      onSent(await api.sendDocument(doc.id, { channel, confirmed, recipientEmail: recipient }));
      setConfirmed(false);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2 border border-slate-700 bg-slate-950/60 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] font-bold text-cyan-200">{String(doc.meta.noticeNumber ?? doc.title)}</span>
        <StatusChip status={doc.status} />
        <span className="ml-auto flex gap-1">
          <button onClick={() => openPdf(doc.id).catch(e => setError(apiErrorMessage(e)))} className="border border-slate-600 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-200 hover:text-cyan-300">PREVIEW PDF</button>
          <button onClick={() => openPdf(doc.id, true, filename).catch(e => setError(apiErrorMessage(e)))} className="border border-slate-600 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-200 hover:text-cyan-300">DOWNLOAD</button>
        </span>
      </div>
      <div className="break-all font-mono text-[9px] text-slate-500">SHA-256 {doc.sha256}</div>

      {last && (
        <div className="border border-slate-800 bg-slate-900/60 p-2 text-[11px] text-slate-300">
          Last dispatch: <span className="font-mono">{String(last.channel).toUpperCase()}</span> · {String(last.at ?? '')}
          {last.recipient ? <> · to <span className="font-mono">{String(last.recipient)}</span></> : null}
          {last.ticketId ? <> · SAHYOG ticket <span className="font-mono">{String(last.ticketId)}</span></> : null}
          {last.note ? <div className="mt-1 text-amber-300">{String(last.note)}</div> : null}
        </div>
      )}

      <div className="space-y-2 border-t border-slate-800 pt-2">
        <div className="flex flex-wrap items-center gap-3 font-mono text-[10px] text-slate-300">
          <span className={labelCls}>Send via</span>
          <label className="flex items-center gap-1"><input type="radio" checked={channel === 'email'} onChange={() => setChannel('email')} /> E-MAIL {email && <span className={email.configured ? 'text-emerald-400' : 'text-amber-400'}>({email.configured ? 'SMTP' : 'OUTBOX: SMTP not set'})</span>}</label>
          <label className="flex items-center gap-1"><input type="radio" checked={channel === 'sahyog'} onChange={() => setChannel('sahyog')} /> SAHYOG PORTAL</label>
        </div>
        <label className="flex items-start gap-2 text-[11px] text-slate-200">
          <input type="checkbox" className="mt-0.5" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
          <span>
            I have reviewed this notice. Send it to <strong className="text-cyan-200">{String(doc.meta.vasp)}</strong>
            {channel === 'email' ? <> at <span className="font-mono">{recipient}</span></> : <> through SAHYOG</>}.
          </span>
        </label>
        <button disabled={!confirmed || busy} onClick={send} className="w-full border border-cyan-600 bg-cyan-900/50 px-3 py-2 font-mono text-[11px] font-bold tracking-wider text-cyan-100 hover:bg-cyan-800 disabled:cursor-not-allowed disabled:opacity-40">
          {busy ? 'SENDING…' : channel === 'email' ? 'SEND NOTICE BY E-MAIL' : 'SUBMIT NOTICE VIA SAHYOG'}
        </button>
        {error && <div className="border border-red-800 bg-red-950/30 p-2 font-mono text-[10px] text-red-300">{error}</div>}
      </div>
    </div>
  );
}

function DraftCard({ runId, draft, email, existing, onChange }: { runId: string; draft: NoticeDraft; email: EmailStatus | null; existing: DocumentSummary[]; onChange: () => void }) {
  const [open, setOpen] = useState(existing.length === 0);
  const [recipient, setRecipient] = useState(draft.recipient.email ?? '');
  const [officer, setOfficer] = useState<Officer>({});
  const [deadline, setDeadline] = useState(7);
  const [records, setRecords] = useState<string[]>(draft.suggestedRecords);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [docs, setDocs] = useState<DocumentSummary[]>(existing);

  useEffect(() => { setOfficer(loadOfficer()); }, []);
  useEffect(() => { setDocs(existing); }, [existing]);

  const setField = (key: keyof Officer, value: string) => {
    const next = { ...officer, [key]: value };
    setOfficer(next);
    saveOfficer(next);
  };

  const generate = async () => {
    setBusy(true);
    setError('');
    try {
      const doc = await api.createNotice(runId, { targetId: draft.targetId, targetAddress: draft.targetAddress, recipientEmail: recipient.trim(), officer, deadlineDays: deadline, records });
      setDocs([doc, ...docs]);
      setOpen(false);
      onChange();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 border border-slate-800 bg-slate-900/40 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-sans text-sm font-bold text-cyan-50">{draft.vasp}</span>
        <span className="border border-slate-600 px-1.5 py-0.5 font-mono text-[9px] text-slate-300">{draft.priority} PRIORITY</span>
        <span className="font-mono text-[10px] text-slate-500" title={draft.targetAddress}>{draft.chain ?? ''} · {shortAddr(draft.targetAddress)}</span>
        <span className="ml-auto font-mono text-[9px] text-amber-300">score {draft.attributionScore.toFixed(2)} · UNCALIBRATED</span>
      </div>

      <div>
        <div className={labelCls}>Platforms reached through OSINT</div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {draft.website && <a href={draft.website} target="_blank" rel="noopener noreferrer" className="border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-[10px] text-cyan-300 hover:border-cyan-600">Website ↗</a>}
          {draft.channels.map(c => (
            <a key={c.platform} href={c.url ?? '#'} target="_blank" rel="noopener noreferrer" className="border border-emerald-800 bg-emerald-950/30 px-2 py-1 font-mono text-[10px] text-emerald-300 hover:border-emerald-500">{c.platform}: {c.handle} ↗</a>
          ))}
          {draft.channels.length === 0 && !draft.website && <span className="text-[11px] text-slate-500">No public channels held for this VASP.</span>}
        </div>
      </div>

      {docs.map(d => <DocumentCard key={d.id} doc={d} email={email} onSent={updated => { setDocs(docs.map(x => (x.id === updated.id ? updated : x))); onChange(); }} />)}

      {!open ? (
        <button onClick={() => setOpen(true)} className="border border-slate-600 bg-slate-800 px-3 py-1.5 font-mono text-[10px] text-slate-200 hover:text-cyan-300">+ NEW NOTICE TO {draft.vasp.toUpperCase()}</button>
      ) : (
        <div className="space-y-3 border-t border-slate-800 pt-3">
          <label className="block">
            <span className={labelCls}>Recipient: law-enforcement contact of {draft.vasp}</span>
            <input className={inputCls} type="email" value={recipient} onChange={e => setRecipient(e.target.value)} placeholder="le-requests@vasp.example" />
            {!draft.recipient.verified && <span className="mt-1 block text-[10px] text-amber-300">No verified contact on file. Enter the address your unit has verified, or add it to the VASP contacts directory.</span>}
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            {([['name', 'Officer name'], ['rank', 'Rank'], ['unit', 'Unit / police station'], ['email', 'Officer e-mail'], ['phone', 'Officer phone']] as const).map(([key, label]) => (
              <label key={key} className="block">
                <span className={labelCls}>{label}</span>
                <input className={inputCls} value={officer[key] ?? ''} onChange={e => setField(key, e.target.value)} />
              </label>
            ))}
            <label className="block">
              <span className={labelCls}>Respond within</span>
              <select className={inputCls} value={deadline} onChange={e => setDeadline(Number(e.target.value))}>
                {[3, 7, 10, 15, 30].map(d => <option key={d} value={d}>{d} days</option>)}
              </select>
            </label>
          </div>
          <div>
            <div className={labelCls}>Records required ({draft.legalBasis})</div>
            <div className="mt-1 space-y-1">
              {draft.suggestedRecords.map(r => (
                <label key={r} className="flex items-start gap-2 text-[11px] text-slate-300">
                  <input type="checkbox" className="mt-0.5" checked={records.includes(r)} onChange={e => setRecords(e.target.checked ? [...records, r] : records.filter(x => x !== r))} />
                  <span>{r}</span>
                </label>
              ))}
            </div>
          </div>
          <button disabled={busy || records.length === 0} onClick={generate} className="w-full border border-teal-600 bg-teal-900/40 px-3 py-2 font-mono text-[11px] font-bold tracking-wider text-teal-100 hover:bg-teal-800 disabled:opacity-40">
            {busy ? 'GENERATING…' : 'GENERATE NOTICE PDF'}
          </button>
          {error && <div className="border border-red-800 bg-red-950/30 p-2 font-mono text-[10px] text-red-300">{error}</div>}
        </div>
      )}
    </div>
  );
}

export function NoticeComposer({ runId }: { runId?: string }) {
  const [drafts, setDrafts] = useState<NoticeDraft[] | null>(null);
  const [email, setEmail] = useState<EmailStatus | null>(null);
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState('');

  const load = () => {
    if (!runId) return;
    Promise.all([api.noticeDrafts(runId), api.documents(runId)])
      .then(([d, list]) => { setDrafts(d.drafts); setEmail(d.email); setDocs(list); })
      .catch(e => setError(apiErrorMessage(e)));
  };

  useEffect(load, [runId]);

  if (error) return <div className="border border-red-800 bg-red-950/30 p-3 font-mono text-xs text-red-300">{error}</div>;
  if (!drafts) return <div className="h-24 animate-pulse border border-slate-800 bg-slate-900/60" />;
  if (drafts.length === 0) {
    return <div className="border border-slate-700 bg-slate-900/40 p-4 text-center text-[11px] text-slate-400">No attributed VASP for this run, so there is nobody to send a notice to.</div>;
  }
  const refreshDocs = () => runId && api.documents(runId).then(setDocs).catch(() => undefined);

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-slate-400">
        One notice per attributed VASP. Generate the PDF, review it, tick the confirmation and send. Every notice is hashed into the evidence chain and logged.
      </p>
      {drafts.map(d => (
        <DraftCard key={`${d.targetId}-${d.targetAddress}`} runId={runId!} draft={d} email={email}
          existing={docs.filter(x => x.kind === 'vasp_notice' && x.meta.targetAddress === d.targetAddress && x.meta.targetId === d.targetId)} onChange={refreshDocs} />
      ))}
    </div>
  );
}
