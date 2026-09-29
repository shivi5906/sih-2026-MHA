// Cytoscape styles and layout for the case graph (components/graph-explorer.tsx).
// Colours match the legend: address = cyan circle, exchange = yellow diamond,
// suspect/seed = red square, virtual (dataset pool) = slate hexagon.

export type NodeType = 'address' | 'exchange' | 'suspect' | 'virtual';

/** Edge/label colour for a taint fraction between 0 and 1. */
export function taintColor(taint: number): string {
  const t = Number.isFinite(taint) ? Math.max(0, Math.min(1, taint)) : 0;
  if (t >= 0.75) return '#ef4444'; // red-500
  if (t >= 0.4) return '#f97316'; // orange-500
  if (t >= 0.1) return '#f59e0b'; // amber-500
  if (t > 0) return '#22d3ee'; // cyan-400
  return '#64748b'; // slate-500
}

/** Force-directed layout for normal graphs, a cheaper one for very large graphs. */
export function getLayoutConfig(elementCount: number): Record<string, unknown> {
  if (elementCount > 600) {
    return { name: 'concentric', animate: false, fit: true, padding: 30, minNodeSpacing: 8 };
  }
  return {
    name: 'cose-bilkent',
    animate: false,
    fit: true,
    padding: 30,
    randomize: true,
    nodeRepulsion: 6000,
    idealEdgeLength: elementCount > 200 ? 60 : 90,
    edgeElasticity: 0.45,
    nestingFactor: 0.1,
    gravity: 0.25,
    numIter: 2500,
    tile: true,
  };
}

export const cytoscapeStylesheet = [
  {
    selector: 'node',
    style: {
      'background-color': '#22d3ee',
      'border-width': 1,
      'border-color': '#0f172a',
      width: 14,
      height: 14,
      label: 'data(label)',
      color: '#cbd5e1',
      'font-size': 8,
      'font-family': 'ui-monospace, SFMono-Regular, Menlo, monospace',
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'text-outline-color': '#020617',
      'text-outline-width': 2,
      'min-zoomed-font-size': 6,
    },
  },
  {
    selector: 'node.exchange',
    style: { 'background-color': '#facc15', 'border-color': '#92400e', 'border-width': 2, shape: 'diamond', width: 24, height: 24, color: '#fde68a', 'font-size': 9 },
  },
  {
    selector: 'node.suspect',
    style: { 'background-color': '#ef4444', 'border-color': '#7f1d1d', 'border-width': 2, shape: 'round-rectangle', width: 20, height: 20, color: '#fecaca' },
  },
  {
    selector: 'node.virtual',
    style: { 'background-color': '#475569', 'border-color': '#94a3b8', 'border-width': 2, shape: 'hexagon', width: 26, height: 26, color: '#e2e8f0', 'font-size': 9 },
  },
  {
    selector: 'node:selected',
    style: { 'border-width': 4, 'border-color': '#f472b6', 'overlay-opacity': 0 },
  },
  {
    selector: 'edge',
    style: {
      width: 1.2,
      'line-color': '#334155',
      'target-arrow-shape': 'triangle',
      'target-arrow-color': '#334155',
      'arrow-scale': 0.7,
      'curve-style': 'bezier',
      opacity: 0.85,
    },
  },
  {
    selector: 'edge[taint > 0]',
    style: { 'line-color': (ele: { data: (k: string) => unknown }) => taintColor(Number(ele.data('taint'))), 'target-arrow-color': (ele: { data: (k: string) => unknown }) => taintColor(Number(ele.data('taint'))) },
  },
  {
    selector: 'edge:selected',
    style: { width: 2.5, 'line-color': '#f472b6', 'target-arrow-color': '#f472b6' },
  },
];
