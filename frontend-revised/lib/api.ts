export type CaseSummary = { id: string; number: string; title: string; status: string };
export type GraphResponse = { nodes: Array<{ id: string; label: string; data?: Record<string, unknown> }>; edges: Array<{ id: string; source: string; target: string; data?: Record<string, unknown>; epistemicLabel?: string }>; banner: string; renderedEdges?: number; totalEdges?: number; truncated?: boolean };
export type Attribution = { id: string; hypothesis: string; score: number; band: string; epistemicLabel: string; supporting: string[]; contradicting: string[]; nextActions: string[] };
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
export const api = {
  login: (email: string, password: string, role: string) => fetchApi<Record<string, unknown>>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password, role }) }),
  me: () => fetchApi<{id: string; name: string; email: string; role: string}>('/auth/me'),
  cases: () => fetchApi<CaseSummary[]>('/cases'),
  createCase: (number: string, title: string, walletAddress?: string, chain?: string) => fetchApi<CaseSummary & { walletAddress?: string }>('/cases', { method: 'POST', body: JSON.stringify({ number, title, walletAddress, chain }) }),
  startInvestigation: (caseId: string, walletAddress?: string, chain?: string) => fetchApi<InvestigationResult>(`/cases/${caseId}/investigations`, { method: 'POST', body: JSON.stringify({ walletAddress, chain }) }),
  graph: (runId: string) => fetchApi<GraphResponse>(`/investigations/${runId}/graph`),
  attribution: (runId: string) => fetchApi<Attribution[]>(`/investigations/${runId}/attribution`),
  evidence: () => fetchApi<Array<Record<string, unknown>>>('/evidence'), verifyEvidence: (id: string) => fetchApi<{ valid: boolean; firstBrokenLink?: string }>(`/evidence/${id}/verify`), audit: () => fetchApi<Array<Record<string, unknown>>>('/audit'), vasps: () => fetchApi<{ items: Array<Record<string, unknown>> }>('/intel/vasps'), reports: (runId: string) => fetchApi<Array<Record<string, unknown>>>(`/investigations/${runId}/reports`),
  prepareSahyog: (id: string) => fetchApi<Record<string, unknown>>(`/attributions/${id}/sahyog/prepare`, { method: 'POST' }), approveSahyog: (id: string) => fetchApi<Record<string, unknown>>(`/attributions/${id}/sahyog/approve`, { method: 'POST' }),
};
