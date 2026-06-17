export interface ObservabilityInput {
  cpu_usage: number;
  memory_usage: number;
  disk_usage?: number;
  error_count: number;
  warn_count?: number;
  alert_volume?: number;
  duration_min?: number;
  impacted_services?: number;
  latency_ms: number;
  error_rate?: number;
  net_in_mbps?: number;
  net_out_mbps?: number;
  request_rate?: number;
  gc_pause_ms?: number;
  thread_count?: number;
  tower?: string;
  service?: string;
}

export interface InvestigationResult {
  incident_id: string;
  severity: "P1 Critical" | "P2 High" | "P3 Medium" | "P4 Low";
  severity_confidence: number;
  anomaly: boolean;
  anomaly_score: number;
  root_cause: string;
  root_cause_confidence: number;
  similar_incidents: Array<{
    incident_id: string;
    summary: string;
    root_cause: string;
    resolution: string;
    score: number;
  }>;
  recommendations: string[];
  report: string;
  report_markdown: string;
  processing_time_ms: number;
}

export interface Incident {
  incident_id: string;
  timestamp: string;
  severity: string;
  severity_confidence: number;
  anomaly: boolean;
  anomaly_score: number;
  root_cause: string;
  root_cause_confidence: number;
  tower: string;
  service: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  error_count: number;
  report_summary: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  models: any;
  vector_db: any;
  database: any;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchWithRetry(url: string, options: RequestInit = {}, retries = 3): Promise<Response> {
  let attempt = 0;
  while (attempt < retries) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      return response;
    } catch (error) {
      attempt++;
      if (attempt >= retries || (error instanceof DOMException && error.name === 'AbortError')) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt - 1))); // Exponential backoff
    }
  }
  throw new Error("Unreachable");
}

export const api = {
  getHealth: async (signal?: AbortSignal): Promise<HealthStatus> => {
    const res = await fetchWithRetry(`${API_BASE_URL}/health`, { signal });
    return res.json();
  },
  
  predictSeverity: async (data: ObservabilityInput, signal?: AbortSignal) => {
    const res = await fetchWithRetry(`${API_BASE_URL}/predict/severity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal,
    });
    return res.json();
  },

  predictAnomaly: async (data: ObservabilityInput, signal?: AbortSignal) => {
    const res = await fetchWithRetry(`${API_BASE_URL}/predict/anomaly`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal,
    });
    return res.json();
  },

  predictRootCause: async (data: ObservabilityInput, signal?: AbortSignal) => {
    const res = await fetchWithRetry(`${API_BASE_URL}/predict/root-cause`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal,
    });
    return res.json();
  },

  investigate: async (data: ObservabilityInput & { incident_id?: string; description?: string }, signal?: AbortSignal): Promise<InvestigationResult> => {
    const res = await fetchWithRetry(`${API_BASE_URL}/investigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal,
    });
    return res.json();
  },

  getIncidents: async (params?: { limit?: number; offset?: number; severity?: string; root_cause?: string; anomaly_only?: boolean }, signal?: AbortSignal) => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());
    if (params?.severity) searchParams.set("severity", params.severity);
    if (params?.root_cause) searchParams.set("root_cause", params.root_cause);
    if (params?.anomaly_only) searchParams.set("anomaly_only", "true");
    
    const url = `${API_BASE_URL}/incidents${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const res = await fetchWithRetry(url, { signal });
    return res.json();
  }
};