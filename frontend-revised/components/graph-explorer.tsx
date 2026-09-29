'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { api, Attribution, GraphResponse } from '@/lib/api';
import { cytoscapeStylesheet, getLayoutConfig, NodeType, taintColor } from '@/lib/graph-styles';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import { CaseDetailHeader } from './case-detail-header';
import { AttributionPanel } from './attribution-panel';
import { OsintPanel } from './osint-panel';

try {
  cytoscape.use(coseBilkent);
} catch (e) {
  // Ignore already registered error
}

const Panel = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="border border-slate-800 bg-slate-950/70 p-4">
    <h2 className="mb-3 font-mono text-xs tracking-wider text-teal-400">{title}</h2>
    {children}
  </section>
);

export function GraphExplorer({ runId }: { runId?: string }) {
  const [graph, setGraph] = useState<GraphResponse>({ nodes: [], edges: [], banner: '' });
  const [items, setItems] = useState<Attribution[]>([]);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [tab, setTab] = useState<'attribution' | 'challenge' | 'replay'>('attribution');
  const [min, setMin] = useState('0');
  const [label, setLabel] = useState('');
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [mode, setMode] = useState<'graph' | 'split'>('graph');
  const [focusNotice, setFocusNotice] = useState('');
  const cyRef = useRef<any>(null);

  useEffect(() => {
    if (runId) {
      setError('');
      void Promise.all([
        api.graph(runId).then(setGraph),
        api.attribution(runId).then(setItems)
      ]).catch(() => setError('Unable to load the case graph.'));
    }
  }, [runId]);

  const focusOptions = useMemo(() => 
    graph.nodes.filter(n => n.id.startsWith('virtual:') || (n.data?.type === 'exchange') || n.label === 'Xzzx.biz'),
    [graph.nodes]
  );

  const elements = useMemo(() => {
    const amount = Number(min);
    const amountFloor = Number.isFinite(amount) && amount >= 0 ? amount : 0;
    
    // Simple mock classification since node classify functions might vary
    const processedNodes = graph.nodes.map(n => {
      let type: NodeType = 'address';
      if (n.id.startsWith('virtual:')) type = 'virtual';
      else if (n.label && n.label.toLowerCase().includes('exchange')) type = 'exchange';
      else if (n.data?.isSuspect) type = 'suspect';
      
      return {
        data: { id: n.id, label: n.label, type, ...n.data },
        classes: type
      };
    });

    const matching = new Set(processedNodes.filter(n => !label || n.data.label === label).map(n => n.data.id));
    
    const processedEdges = graph.edges
      .filter(e => Number(e.data?.amount ?? 0) >= amountFloor && (!label || matching.has(e.source) || matching.has(e.target)))
      .map(e => ({
        data: { id: e.id, source: e.source, target: e.target, taint: e.data?.taint ?? 0, ...e.data }
      }));

    const connected = new Set(processedEdges.flatMap(e => [e.data.source, e.data.target]));
    
    return [
      ...processedNodes.filter(n => connected.has(n.data.id)),
      ...processedEdges
    ];
  }, [graph, label, min]);

  const reset = () => {
    setMin('0');
    setLabel('');
    setSelected(null);
    cyRef.current?.fit(undefined, 40);
  };

  const zoom = (factor: number) => cyRef.current?.zoom(cyRef.current.zoom() * factor);

  // Re-fit after the graph data arrives and whenever the container width changes (split view, side panel).
  useEffect(() => {
    const timer = setTimeout(() => {
      cyRef.current?.resize();
      cyRef.current?.fit(undefined, 40);
    }, 150);
    return () => clearTimeout(timer);
  }, [elements, mode, rightPanelOpen]);

  const focusAddress = (address: string) => {
    const cy = cyRef.current;
    const node = cy?.getElementById(address);
    if (!cy || !node || node.empty()) {
      setFocusNotice(`${address.slice(0, 12)}… is not in the rendered graph. Reset filters, or it may be outside the rendered overview.`);
      return;
    }
    setFocusNotice('');
    cy.elements().unselect();
    node.select();
    cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.2) }, { duration: 400 });
    setSelected(node.data());
  };

  return (
    <div className="space-y-4">
      <CaseDetailHeader 
        caseTitle={`Case ${runId ? runId.slice(0, 8) : 'Pending'}`} 
        traceMode={graph.banner.includes('REPLAY') ? 'replay' : 'live'}
      />
      
      {error && <div className="border border-red-800 bg-red-950/30 p-3 font-mono text-xs text-red-300">{error}</div>}

      <div className="flex flex-wrap items-center gap-1 border-b border-slate-800">
        {([['graph', 'GRAPH VIEW'], ['split', 'SPLIT VIEW: GRAPH + OSINT']] as const).map(([key, name]) => (
          <button
            key={key}
            onClick={() => setMode(key)}
            className={`px-3 py-2 font-mono text-[10px] tracking-wider transition-colors ${
              mode === key ? 'border-b-2 border-cyan-400 bg-cyan-950/40 font-bold text-cyan-200' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {name}
          </button>
        ))}
        <span className="ml-auto pb-1 font-mono text-[9px] text-slate-500">OSINT runs on the highest-scoring attributed VASPs · UNCALIBRATED</span>
      </div>

      <div className={`grid gap-4 ${mode === 'split' ? 'xl:grid-cols-2' : rightPanelOpen ? 'lg:grid-cols-[1fr_320px]' : 'grid-cols-1'}`}>
        <Panel title="GRAPH VISUALIZATION">
          {/* Toolbar */}
          <div className="mb-4 flex flex-wrap items-end gap-3 rounded border border-slate-800 bg-slate-900/50 p-2">
            <label className="font-mono text-[10px] text-cyan-200 flex-1 min-w-[120px]">
              MINIMUM AMOUNT
              <input 
                className="mt-1 block w-full border border-slate-700 bg-slate-950 p-1.5 text-sm text-white focus:border-cyan-500 focus:outline-none" 
                type="number" min="0" value={min} onChange={e => setMin(e.target.value)} placeholder="0"
              />
            </label>
            <label className="font-mono text-[10px] text-cyan-200 flex-1 min-w-[160px]">
              FOCUS LABEL
              <select 
                className="mt-1 block w-full border border-slate-700 bg-slate-950 p-1.5 text-sm text-white focus:border-cyan-500 focus:outline-none" 
                value={label} onChange={e => setLabel(e.target.value)}
              >
                <option value="">All transfers — recommended</option>
                {focusOptions.map(node => <option key={node.id} value={node.label}>{node.label}</option>)}
              </select>
            </label>
            <button className="border border-cyan-700 bg-cyan-950/50 px-3 py-1.5 font-mono text-[10px] text-cyan-100 hover:bg-cyan-900 transition-colors" onClick={reset}>
              RESET FILTERS
            </button>
            <div className="ml-auto flex gap-1 border-l border-slate-700 pl-3">
              <button className="border border-slate-600 bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700 hover:text-cyan-300" onClick={() => cyRef.current?.fit(undefined, 40)}>FIT</button>
              <button className="border border-slate-600 bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700 hover:text-cyan-300" onClick={() => zoom(1.2)}>+</button>
              <button className="border border-slate-600 bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700 hover:text-cyan-300" onClick={() => zoom(0.8)}>−</button>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="mb-3 flex flex-wrap gap-2 font-mono text-[10px]">
            <div className="flex-1 border border-cyan-800 bg-cyan-950/30 p-2 text-cyan-100 flex items-center justify-between">
              <span>VISIBLE TRANSFERS</span>
              <span className="text-sm font-bold">{graph.renderedEdges ?? graph.edges.length}</span>
            </div>
            <div className="flex-1 border border-sky-800 bg-sky-950/30 p-2 text-sky-100 flex items-center justify-between">
              <span>VISIBLE ADDRESSES</span>
              <span className="text-sm font-bold">{graph.nodes.length}</span>
            </div>
            <div className="flex-1 border border-amber-700 bg-amber-950/30 p-2 text-amber-200 flex items-center justify-between">
              <span>CALIBRATION</span>
              <span className="text-sm font-bold text-amber-400">UNCALIBRATED</span>
            </div>
          </div>

          {/* Legend */}
          <div className="mb-2 flex flex-wrap items-center gap-4 font-mono text-[10px] text-slate-300 border-b border-slate-800 pb-2">
            <span className="flex items-center gap-1.5"><div className="h-3 w-3 bg-cyan-400 rounded-full border border-slate-900"></div> Address</span>
            <span className="flex items-center gap-1.5"><div className="h-3 w-3 bg-yellow-400 rotate-45 border border-amber-800"></div> Exchange</span>
            <span className="flex items-center gap-1.5"><div className="h-3 w-3 bg-red-500 rounded-sm border border-red-900"></div> Suspect/Seed</span>
            <span className="flex items-center gap-1.5 ml-auto text-slate-400">{graph.banner}</span>
          </div>

          {/* Graph Area */}
          <div className="relative border border-slate-700 bg-slate-950 rounded-sm overflow-hidden h-[500px]">
            {elements.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center p-6 text-center font-mono text-sm text-slate-400">
                No transfers match these filters. Select RESET FILTERS to show the graph.
              </div>
            ) : (
              <CytoscapeComponent 
                elements={elements} 
                layout={getLayoutConfig(elements.length)}
                style={{ height: '100%', width: '100%' }} 
                stylesheet={cytoscapeStylesheet as any} 
                cy={cy => {
                  cyRef.current = cy;
                  cy.off('tap', 'node');
                  cy.on('tap', 'node', event => setSelected(event.target.data()));
                  // cose-bilkent ignores its own fit option, so fit once each layout finishes.
                  cy.off('layoutstop');
                  cy.on('layoutstop', () => cy.fit(undefined, 40));
                }}
              />
            )}
            
            {/* Toggle Panel Button overlay */}
            {mode === 'graph' && <button 
              onClick={() => setRightPanelOpen(!rightPanelOpen)}
              className="absolute top-2 right-2 border border-slate-600 bg-slate-800/80 p-1.5 text-slate-300 hover:bg-slate-700 hover:text-cyan-300 z-10 rounded backdrop-blur-sm"
              title={rightPanelOpen ? "Close Details Panel" : "Open Details Panel"}
            >
              {rightPanelOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
              )}
            </button>}
          </div>
          {focusNotice && <div className="mt-2 border border-amber-800 bg-amber-950/30 p-2 font-mono text-[10px] text-amber-300">{focusNotice}</div>}
          {mode === 'split' && selected && (
            <div className="mt-2 flex flex-wrap items-center gap-2 border border-slate-800 bg-slate-900/60 p-2 font-mono text-[10px]">
              <span className="text-slate-500">SELECTED</span>
              <span className="font-bold text-cyan-300">{String(selected.label || 'Unknown')}</span>
              {selected.address ? <span className="break-all text-slate-400">{String(selected.address)}</span> : null}
            </div>
          )}
        </Panel>

        {mode === 'split' && (
          <Panel title="OSINT INTELLIGENCE">
            <div className="max-h-[820px] overflow-y-auto pr-1">
              <OsintPanel runId={runId} onFocusAddress={focusAddress} />
            </div>
          </Panel>
        )}

        {/* Right Panel */}
        {mode === 'graph' && rightPanelOpen && (
          <div className="flex flex-col gap-4">
            <Panel title="NODE DETAILS">
              {selected ? (
                <div className="space-y-3">
                  <div className="rounded border border-slate-700 bg-slate-900 p-3 break-words">
                    <div className="font-mono text-[10px] text-slate-500 mb-1 uppercase">{selected.type || 'ADDRESS'}</div>
                    <div className="font-mono text-sm text-cyan-300 font-bold mb-2">
                      {String(selected.label || 'Unknown')}
                    </div>
                    {selected.address && (
                      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-800">
                        <span className="font-mono text-xs text-slate-400 break-all">{String(selected.address)}</span>
                      </div>
                    )}
                  </div>
                  {selected.taint !== undefined && (
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <span className="font-mono text-[10px] text-slate-400">TAINT FRACTION</span>
                      <span className="font-mono text-xs font-bold" style={{color: taintColor(Number(selected.taint))}}>
                        {(Number(selected.taint) * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex h-32 items-center justify-center border border-dashed border-slate-700 bg-slate-900/30 p-4 text-center text-sm text-slate-500">
                  Select a node in the graph to view details
                </div>
              )}
            </Panel>

            <Panel title="ANALYSIS">
              <div className="flex gap-1 border-b border-slate-800 pb-2">
                {(['attribution', 'challenge', 'replay'] as const).map(t => (
                  <button 
                    key={t} 
                    onClick={() => setTab(t)} 
                    className={`px-2 py-1 font-mono text-[10px] transition-colors ${
                      tab === t 
                        ? 'bg-teal-950/50 text-teal-300 border-b-2 border-teal-500 font-bold' 
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {t.toUpperCase()}
                  </button>
                ))}
              </div>
              
              <div className="mt-2 h-full min-h-[300px]">
                {tab === 'attribution' && <AttributionPanel items={items} />} 
                {tab === 'challenge' && (
                  <div className="space-y-4 pt-4 text-xs">
                    <div>
                      <h4 className="font-mono text-[10px] text-slate-500 mb-1">ALTERNATIVES</h4>
                      <p className="text-slate-300">{items.slice(1).map(x => x.hypothesis).join(', ') || 'NO_ATTRIBUTION'}</p>
                    </div>
                    <div>
                      <h4 className="font-mono text-[10px] text-amber-500 mb-1">CONTRADICTING EVIDENCE</h4>
                      <p className="text-slate-300">{items[0]?.contradicting.join(', ') || 'None identified'}</p>
                    </div>
                    <div>
                      <h4 className="font-mono text-[10px] text-cyan-500 mb-1">EVIDENCE GAPS</h4>
                      <p className="text-slate-300">{items[0]?.nextActions.join(' ') || 'Second independent source required.'}</p>
                    </div>
                    <div className="border border-amber-900/50 bg-amber-950/20 p-2 text-amber-400">
                      <strong>Sensitivity:</strong> removing the tier-C label changes the conclusion to NO_ATTRIBUTION.
                    </div>
                  </div>
                )} 
                {tab === 'replay' && (
                  <div className="pt-4 text-xs">
                    <h4 className="font-mono text-[10px] text-slate-500 mb-4">TIMELINE STEP</h4>
                    <input className="w-full accent-teal-500" type="range" min="1" max="3" defaultValue="1" />
                    <div className="mt-4 border border-teal-900/50 bg-teal-950/20 p-3 text-teal-300 font-mono">
                      SNAPSHOT / CASE REPLAY trace event.
                    </div>
                  </div>
                )}
              </div>
            </Panel>
          </div>
        )}
      </div>
    </div>
  );
}
