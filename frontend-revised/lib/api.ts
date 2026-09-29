export type CaseSummary = { id: string; number: string; title: string; status: string };
export type GraphResponse = { nodes: Array<{ id: string; label: string; data?: Record<string, unknown> }>; edges: Array<{ id: string; source: string; target: string; data?: Record<string, unknown>; epistemicLabel?: string }>; banner: string; renderedEdges?: number; totalEdges?: number; truncated?: boolean };
export type Attribution = { id: string; hypothesis: string; score: number; band: string; epistemicLabel: string; supporting: string[]; contradicting: string[]; nextActions: string[] };
export type OsintChannel = { platform: string; handle: string | null; url: string | null; status: 'FOUND' | 'NOT_FOUND' | 'NOT_PUBLIC'; epistemicLabel: string; source: string; note: string };
export type OsintTarget = {
  id: string; vasp: string; targetAddress: string; chain: string | null; attributionScore: number; band: string; priority: 'HIGH' | 'MEDIUM' | 'LOW'; epistemicLabel: string;
  osintCoverage: number; investigationPriority: number; calibrated: boolean;
  profile: { entityType: string; website: string | null; inRegistry: boolean; knownHotWallet: boolean; note: string | null };
  inflow: { txCount: number; totalValue: number; asset: string | null; uniqueSenders: number; firstSeen: string | null; lastSeen: string | null };
  channels: OsintChannel[];
  accountHolder: { status: string; fields: string[]; route: string; epistemicLabel: string };
  pivots: Array<{ name: string; kind: string; url: string }>;
  connectors: Array<{ name: string; purpose: string; status: string; mock: boolean }>;
  supporting: string[]; nextActions: string[];
};
export type GraphAnalytics = {
  nodes: number; edges: number; uniqueLinks: number; totalValue: number; asset: string | null; density: number; components: number; sources: number; sinks: number;
  valueIntoVasps: number; valueIntoVaspsShare: number;
  topHubs: Array<{ address: string; inDegree: number; outDegree: number; value: number; isVasp: boolean }>;
  valueBuckets: Array<{ label: string; count: number }>;
  timeline: Array<{ month: string; count: number; value: number }>;
  datasets: Array<{ name: string; count: number }>;
  hopDistribution: Array<{ hop: number; count: number }>;
  epistemicLabel: string;
};
export type OsintReport = {
  runId: string; banner: string; generatedAt: string; calibrated: boolean; sahyogMock: boolean; connectorsLive: boolean;
  summary: { targets: number; highPriority: number; channelsFound: number; channelsChecked: number; hypothesesConsidered: number };
  targets: OsintTarget[]; graphAnalytics: GraphAnalytics; disclaimer: string;
};
export type DocumentSummary = {
  id: string; caseId: string; runId: string; kind: 'vasp_notice' | 'court_report'; title: string; status: string; sha256: string;
  createdBy: string; createdAt: string | null; sizeBytes: number; meta: Record<string, any>;
};
export type NoticeDraft = {
  targetId: string; vasp: string; targetAddress: string; chain: string | null; attributionScore: number; band: string; priority: string; website: string | null;
  recipient: { email: string | null; portal: string | null; verified: boolean; source: string | null };
  channels: OsintChannel[]; inflow: OsintTarget['inflow']; suggestedRecords: string[]; legalBasis: string; calibrated: boolean;
};
export type EmailStatus = { mode: 'smtp' | 'outbox'; configured: boolean; host: string | null; port: number; sender: string | null };
export type SahyogStatus = { mode: 'mock' | 'live'; configured: boolean; baseUrl?: string | null; auth?: string; health?: Record<string, unknown> | null; [key: string]: unknown };
export type IntegrationsStatus = { email: EmailStatus; sahyog: SahyogStatus };
export type Officer = { name?: string; rank?: string; unit?: string; email?: string; phone?: string };
export type InvestigationResult = { id: string; status: string; manifest?: Record<string, unknown>; error?: string };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export class ApiOfflineError extends Error { constructor() { super('API offline'); } }
async function fetchApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const role = typeof window === 'undefined' ? 'Analyst' : window.localStorage.getItem('vault-x-role') ?? 'Analyst';
  const token = typeof window === 'undefined' ? null : window.localStorage.getItem('vault-x-token');
  
  const headers: HeadersInit = { 
    'Content-Type': 'application/json', 
    'X-Role': role, 
    ...init.headers 
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  try { 
    const response = await fetch(`${API_URL}/api/v1${path}`, { ...init, headers }); 
    if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`); 
    return response.json() as Promise<T>; 
  }
  catch (error) { 
    if (error instanceof TypeError) throw new ApiOfflineError(); 
    throw error; 
  }
}
/** Error text for display: the API's "detail" message when present. */
export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiOfflineError) return 'API offline. Start the backend and try again.';
  const text = error instanceof Error ? error.message : String(error);
  const match = text.match(/^\d+: ([\s\S]*)$/);
  if (match) {
    try { const body = JSON.parse(match[1]); if (typeof body.detail === 'string') return body.detail; } catch { /* not JSON */ }
    return match[1];
  }
  return text;
}
/** Fetches a PDF with the session's auth headers and returns an object URL for viewing or download. */
export async function fetchPdfUrl(path: string): Promise<string> {
  const role = window.localStorage.getItem('vault-x-role') ?? 'Analyst';
  const token = window.localStorage.getItem('vault-x-token');
  const headers: Record<string, string> = { 'X-Role': role };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try { response = await fetch(`${API_URL}/api/v1${path}`, { headers }); } catch { throw new ApiOfflineError(); }
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return URL.createObjectURL(await response.blob());
}
export const api = {
  login: (email: string, password: string, role: string) => fetchApi<Record<string, unknown>>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password, role }) }),
  me: () => fetchApi<{id: string; name: string; email: string; role: string}>('/auth/me'),
  cases: () => fetchApi<CaseSummary[]>('/cases'),
  createCase: (number: string, title: string, walletAddress?: string, chain?: string) => fetchApi<CaseSummary & { walletAddress?: string }>('/cases', { method: 'POST', body: JSON.stringify({ number, title, walletAddress, chain }) }),
  startInvestigation: (caseId: string, walletAddress?: string, chain?: string) => fetchApi<InvestigationResult>(`/cases/${caseId}/investigations`, { method: 'POST', body: JSON.stringify({ walletAddress, chain }) }),
  graph: (runId: string) => fetchApi<GraphResponse>(`/investigations/${runId}/graph`),
  attribution: (runId: string) => fetchApi<Attribution[]>(`/investigations/${runId}/attribution`),
  osint: (runId: string) => fetchApi<OsintReport>(`/investigations/${runId}/osint`),
  evidence: () => fetchApi<Array<Record<string, unknown>>>('/evidence'), verifyEvidence: (id: string) => fetchApi<{ valid: boolean; firstBrokenLink?: string }>(`/evidence/${id}/verify`), audit: () => fetchApi<Array<Record<string, unknown>>>('/audit'), vasps: () => fetchApi<{ items: Array<Record<string, unknown>> }>('/intel/vasps'), reports: (runId: string) => fetchApi<Array<Record<string, unknown>>>(`/investigations/${runId}/reports`),
  integrationsStatus: () => fetchApi<IntegrationsStatus>('/integrations/status'),
  noticeDrafts: (runId: string) => fetchApi<{ banner: string; email: EmailStatus; drafts: NoticeDraft[] }>(`/investigations/${runId}/notices/drafts`),
  createNotice: (runId: string, body: { targetId: string; targetAddress: string; recipientEmail: string; officer: Officer; deadlineDays: number; records: string[] }) =>
    fetchApi<DocumentSummary>(`/investigations/${runId}/notices`, { method: 'POST', body: JSON.stringify(body) }),
  documents: (runId: string) => fetchApi<DocumentSummary[]>(`/investigations/${runId}/documents`),
  sendDocument: (id: string, body: { channel: 'email' | 'sahyog'; confirmed: boolean; recipientEmail?: string }) =>
    fetchApi<DocumentSummary>(`/documents/${id}/send`, { method: 'POST', body: JSON.stringify(body) }),
  prepareSahyog: (id: string) => fetchApi<Record<string, unknown>>(`/attributions/${id}/sahyog/prepare`, { method: 'POST' }), approveSahyog: (id: string) => fetchApi<Record<string, unknown>>(`/attributions/${id}/sahyog/approve`, { method: 'POST' }),
};
