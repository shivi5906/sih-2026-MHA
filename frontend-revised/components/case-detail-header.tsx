'use client';

interface CaseDetailHeaderProps {
  caseTitle?: string;
  caseNumber?: string;
  walletAddress?: string;
  chain?: string;
  traceMode?: 'live' | 'replay';
  onRetrace?: () => void;
}

export function CaseDetailHeader({
  caseTitle = 'Unknown Case',
  caseNumber = 'CASE-000',
  walletAddress,
  chain = 'auto',
  traceMode = 'replay',
  onRetrace
}: CaseDetailHeaderProps) {
  
  const getChainColor = (c: string) => {
    const l = c.toLowerCase();
    if (l.includes('btc') || l.includes('bitcoin')) return 'border-orange-500/50 bg-orange-950/30 text-orange-400';
    if (l.includes('eth') || l.includes('ethereum')) return 'border-purple-500/50 bg-purple-950/30 text-purple-400';
    if (l.includes('trx') || l.includes('tron')) return 'border-red-500/50 bg-red-950/30 text-red-400';
    return 'border-slate-500/50 bg-slate-900/30 text-slate-400';
  };

  return (
    <div className="mb-4 flex flex-col justify-between gap-4 border border-slate-800 bg-slate-950/70 p-3 md:flex-row md:items-center">
      <div className="flex flex-wrap items-center gap-3">
        <div className="font-mono text-sm font-bold text-teal-500">{caseNumber}</div>
        <div className="h-4 w-px bg-slate-700"></div>
        <div className="font-sans text-sm font-medium text-slate-200">{caseTitle}</div>
        
        {walletAddress && (
          <>
            <div className="h-4 w-px bg-slate-700"></div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-slate-400">
                {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
              </span>
              <button 
                onClick={() => navigator.clipboard.writeText(walletAddress)}
                className="text-slate-500 hover:text-cyan-400"
                title="Copy address"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
              </button>
            </div>
          </>
        )}
        
        <div className="h-4 w-px bg-slate-700"></div>
        <div className={`px-2 py-0.5 font-mono text-[10px] uppercase border ${getChainColor(chain)}`}>
          {chain}
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 border border-slate-800 px-2 py-1 font-mono text-[10px]">
          {traceMode === 'live' ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
              </span>
              <span className="text-emerald-400">LIVE TRACE</span>
            </>
          ) : (
            <>
              <span className="h-2 w-2 rounded-full bg-amber-500"></span>
              <span className="text-amber-400">CASE REPLAY</span>
            </>
          )}
        </div>
        
        <div className="flex gap-2">
          {onRetrace && (
            <button 
              onClick={onRetrace}
              className="border border-slate-700 px-3 py-1 font-mono text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition-colors"
            >
              Re-trace
            </button>
          )}
          <button className="border border-slate-700 px-3 py-1 font-mono text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition-colors">
            Export PNG
          </button>
        </div>
      </div>
    </div>
  );
}
