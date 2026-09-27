// Core data types for VAULT-X
export type UserRole = 'Analyst' | 'Senior Investigator' | 'Supervisor' | 'Auditor';

export type Chain = 'Bitcoin' | 'Ethereum' | 'Monero' | 'Ripple' | 'Stablecoin';

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'cleared';

export type CaseStatus = 'open' | 'under_review' | 'pending_approval' | 'approved' | 'archived';

export type EpistemicLabel = 'CONFIRMED' | 'AMBIGUOUS' | 'NO_ATTRIBUTION' | 'CONTRADICTED';

export type EvidenceType =
  | 'deposit_match'
  | 'hot_wallet_forward'
  | 'sweep_behavior'
  | 'cluster'
  | 'external_label'
  | 'contradiction'
  | 'mixer_contamination'
  | 'cross_chain_link';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

export interface Session {
  user: User;
  token: string;
}

export interface Address {
  id: string;
  address: string;
  chain: Chain;
  label?: string;
  riskLevel: RiskLevel;
  entityType?: 'personal' | 'exchange' | 'mixer' | 'unknown';
  tags: string[];
  lastSeen?: number;
}

export interface NormalizedTx {
  id: string;
  txHash: string;
  from: string;
  to: string;
  amount: number;
  asset: string;
  timestamp: number;
  chain: Chain;
  fee?: number;
  blockNumber?: number;
  confidence: number; // 0-1 score
}

export interface Evidence {
  id: string;
  caseId: string;
  type: EvidenceType;
  source: string;
  timestamp: number;
  weight: number; // 0-1
  confidence: number; // 0-1
  description: string;
  verified: boolean;
  hash: string; // integrity/hash-chain
}

export interface AttributionHypothesis {
  id: string;
  caseId: string;
  targetAddress: string;
  hypothesis: string;
  score: number; // 0-1
  epistemicLabel: EpistemicLabel;
  signals: {
    type: EvidenceType;
    weight: number;
    confidence: number;
  }[];
  contradictions: string[];
  nextActions: string[];
}

export interface CaseDetail {
  id: string;
  number: string;
  title: string;
  description: string;
  status: CaseStatus;
  chain: Chain;
  seedAddresses: Address[];
  riskLevel: RiskLevel;
  createdAt: number;
  createdBy: string;
  assignedTo: string;
  lastModified: number;
  graphState: {
    nodeCount: number;
    edgeCount: number;
    maxHopDepth: number;
  };
  tags: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  data: {
    address: string;
    chain: Chain;
    riskLevel: RiskLevel;
    entityType?: string;
    verified?: boolean;
    tags: string[];
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  data: {
    txHash: string;
    amount: number;
    asset: string;
    timestamp: number;
    count?: number; // aggregated tx count
  };
}

export interface VASP {
  id: string;
  name: string;
  aliases: string[];
  jurisdiction: string;
  license?: string;
  tier: 'tier1' | 'tier2' | 'tier3' | 'unknown';
  source: string;
  lastUpdated: number;
  addresses: string[];
}

export interface AuditEntry {
  id: string;
  timestamp: number;
  userId: string;
  userName: string;
  action: string;
  caseId?: string;
  details: Record<string, unknown>;
  hash: string; // for chain integrity
  previousHash: string;
}

export interface RunManifest {
  id: string;
  caseId: string;
  traceSteps: {
    step: number;
    action: string;
    timestamp: number;
    nodeDelta: number;
    edgeDelta: number;
  }[];
  completedAt?: number;
  status: 'running' | 'completed' | 'paused';
}

export interface SAHYOGReferral {
  caseId: string;
  caseTitle: string;
  seedAddresses: Address[];
  hypothesis: AttributionHypothesis;
  evidence: Evidence[];
  timestamp: number;
  submittedBy: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'rejected';
}
