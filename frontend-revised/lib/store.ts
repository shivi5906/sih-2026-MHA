// Simple store for app state (in production, replace with Zustand or server state)
import type { CaseDetail, Address, NormalizedTx, AttributionHypothesis, Evidence } from './types';

// Mock data
const mockCases: CaseDetail[] = Array.from({ length: 8 }, (_, i) => ({
  id: `case-${i + 1}`,
  number: `VAULT-${String(i + 1).padStart(5, '0')}`,
  title: `Investigation ${i + 1}: ${['High-value theft', 'Mixer cluster', 'Exchange fraud', 'Cross-chain trace', 'Darkweb link'][i % 5]}`,
  description: 'Blockchain transaction analysis and attribution investigation',
  status: (['open', 'under_review', 'pending_approval', 'approved', 'archived'][i % 5] as any),
  chain: (['Bitcoin', 'Ethereum', 'Monero', 'Ripple', 'Stablecoin'][i % 5] as any),
  seedAddresses: [
    {
      id: `addr-${i}-1`,
      address: `${i % 2 === 0 ? '1A1z' : '0x'}${Math.random().toString(16).slice(2, 10).toUpperCase()}...`,
      chain: (['Bitcoin', 'Ethereum'][i % 2] as any),
      riskLevel: (['critical', 'high', 'medium', 'low', 'cleared'][Math.floor(Math.random() * 5)] as any),
      tags: ['seed', 'primary'],
    },
  ],
  riskLevel: (['critical', 'high', 'medium', 'low', 'cleared'][i % 5] as any),
  createdAt: Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000,
  createdBy: `analyst-${(i % 5) + 1}`,
  assignedTo: `investigator-${(i % 8) + 1}`,
  lastModified: Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000,
  graphState: {
    nodeCount: 12 + Math.floor(Math.random() * 140),
    edgeCount: 20 + Math.floor(Math.random() * 200),
    maxHopDepth: 3 + Math.floor(Math.random() * 4),
  },
  tags: ['active', 'high-priority', 'mixer-involved'][Math.floor(Math.random() * 3)] ? ['active', 'high-priority'] : ['low-priority'],
}));

let cases = [...mockCases];
let currentCaseId: string | null = null;

export const store = {
  getCases: (): CaseDetail[] => cases,

  getCaseById: (id: string): CaseDetail | undefined => cases.find((c) => c.id === id),

  createCase: (caseData: Partial<CaseDetail>): CaseDetail => {
    const newCase: CaseDetail = {
      id: `case-${Date.now()}`,
      number: `VAULT-${String(cases.length + 1).padStart(5, '0')}`,
      title: caseData.title || 'New Case',
      description: caseData.description || '',
      status: 'open',
      chain: caseData.chain || 'Bitcoin',
      seedAddresses: caseData.seedAddresses || [],
      riskLevel: caseData.riskLevel || 'medium',
      createdAt: Date.now(),
      createdBy: caseData.createdBy || 'system',
      assignedTo: caseData.assignedTo || 'unassigned',
      lastModified: Date.now(),
      graphState: {
        nodeCount: 1,
        edgeCount: 0,
        maxHopDepth: 0,
      },
      tags: caseData.tags || [],
    };
    cases.push(newCase);
    return newCase;
  },

  setCurrentCase: (id: string) => {
    currentCaseId = id;
  },

  getCurrentCaseId: (): string | null => currentCaseId,

  updateCase: (id: string, updates: Partial<CaseDetail>) => {
    const idx = cases.findIndex((c) => c.id === id);
    if (idx !== -1) {
      cases[idx] = { ...cases[idx], ...updates, lastModified: Date.now() };
    }
  },

  // Mock graph data for investigation screen
  getGraphForCase: (caseId: string) => {
    const mockNodes = Array.from({ length: 25 }, (_, i) => ({
      data: {
        id: `node-${i}`,
        label: `${i === 0 ? 'SEED' : ''} ${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
        riskLevel: (['critical', 'high', 'medium', 'low'][Math.floor(Math.random() * 4)] as any),
      },
    }));

    const mockEdges = Array.from({ length: 40 }, (_, i) => ({
      data: {
        id: `edge-${i}`,
        source: `node-${Math.floor(Math.random() * 24)}`,
        target: `node-${Math.floor(Math.random() * 24)}`,
        label: `${(Math.random() * 10).toFixed(2)} BTC`,
      },
    }));

    return { nodes: mockNodes, edges: mockEdges };
  },
};
