// ──────────────────────────────────────────────────────────────────
// Mock data layer for the observability dashboard.
//
// Everything here is deterministic: the same set of filters always
// produces the same result, but different filters produce different
// results. This lets the UI feel "live" without a backend.
// ──────────────────────────────────────────────────────────────────

export interface RootCauseInfo {
  name: string;
  description: string;
  contributingFactors: string[];
  remediation: string;
  typicalSeverity: SeverityLabel;
}

export type SeverityLabel = "P1 Critical" | "P2 High" | "P3 Medium" | "P4 Low";

export const SEVERITY_LEVEL: Record<SeverityLabel, number> = {
  "P4 Low": 1,
  "P3 Medium": 2,
  "P2 High": 3,
  "P1 Critical": 4,
};

export const SEVERITY_BY_LEVEL: Record<number, SeverityLabel> = {
  1: "P4 Low",
  2: "P3 Medium",
  3: "P2 High",
  4: "P1 Critical",
};

// Geographical circles available as a dashboard filter.
export const CIRCLES = [
  "Circle 1",
  "Circle 2",
  "Circle 3",
  "Circle 4",
];

// Business areas available as a dashboard filter.
export const BUSINESS_AREAS = ["BA1", "BA2", "BA3", "BA4"];

// Hourly time slots (00:00 .. 23:00).
export const HOURS: string[] = Array.from({ length: 24 }, (_, h) =>
  `${String(h).padStart(2, "0")}:00`,
);

// The catalogue of root causes, with the context shown on hover.
export const ROOT_CAUSES: RootCauseInfo[] = [
  {
    name: "Network Failure",
    description:
      "Connectivity loss or severe packet drop between services causing request timeouts.",
    contributingFactors: ["switch/router fault", "DNS resolution failure", "TLS handshake errors"],
    remediation: "Reroute traffic, fail over to healthy AZ, restart affected network agents.",
    typicalSeverity: "P1 Critical",
  },
  {
    name: "Database Failure",
    description:
      "Primary database unavailable or degraded, leading to elevated query latency and errors.",
    contributingFactors: ["disk I/O saturation", "query overload", "replication lag"],
    remediation: "Restart DB service, check replication, restore from backup if needed.",
    typicalSeverity: "P1 Critical",
  },
  {
    name: "CPU Saturation",
    description:
      "Sustained high CPU utilisation throttling request processing across the service.",
    contributingFactors: ["traffic spike", "inefficient code path", "noisy neighbour"],
    remediation: "Scale out replicas, enable autoscaling, profile hot code paths.",
    typicalSeverity: "P2 High",
  },
  {
    name: "Service Crash",
    description:
      "Application process terminated unexpectedly, dropping in-flight requests.",
    contributingFactors: ["unhandled exception", "OOM kill", "bad deployment"],
    remediation: "Roll back last deploy, restart service, inspect crash logs.",
    typicalSeverity: "P2 High",
  },
  {
    name: "Disk Failure",
    description:
      "Storage volume degraded or full, blocking writes and corrupting state.",
    contributingFactors: ["bad sectors", "filesystem corruption", "volume full"],
    remediation: "Replace faulty disk, restore RAID, clear logs, expand volume.",
    typicalSeverity: "P2 High",
  },
  {
    name: "Cloud Resource Exhaustion",
    description:
      "Cloud quota or capacity limit reached, preventing new resource allocation.",
    contributingFactors: ["quota exceeded", "AZ capacity limit", "IP exhaustion"],
    remediation: "Request quota increase, rebalance across regions, release idle resources.",
    typicalSeverity: "P3 Medium",
  },
  {
    name: "Memory Leak",
    description:
      "Gradual memory growth leading to GC pressure and eventual OOM conditions.",
    contributingFactors: ["unbounded cache", "leaked references", "large GC pauses"],
    remediation: "Restart affected pods, patch leak, cap cache size, tune GC.",
    typicalSeverity: "P3 Medium",
  },
  {
    name: "Kubernetes Pod Failure",
    description:
      "Pods stuck in CrashLoopBackOff or evicted, reducing available capacity.",
    contributingFactors: ["failed liveness probe", "image pull error", "node pressure"],
    remediation: "Fix probe config, re-pull image, cordon/drain unhealthy nodes.",
    typicalSeverity: "P3 Medium",
  },
];

export const ROOT_CAUSE_NAMES = ROOT_CAUSES.map((rc) => rc.name);

export function getRootCauseInfo(name: string): RootCauseInfo | undefined {
  return ROOT_CAUSES.find((rc) => rc.name === name);
}

// ── deterministic pseudo-random generator (mulberry32) ─────────────
function hashSeed(str: string): number {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ── Mock historical incidents ─────────────────────────────────────
const SERVICES = [
  "api-gateway",
  "payment-service",
  "auth-service",
  "order-service",
  "search-service",
  "notification-service",
];

const TOWERS = ["Application", "Infrastructure", "Database", "Network"];

export interface MockIncident {
  incident_id: string;
  timestamp: string; // ISO
  severity: SeverityLabel;
  root_cause: string;
  service: string;
  tower: string;
  anomaly: boolean;
  error_count: number;
}

/**
 * Deterministically generate the full pool of historical incidents spread
 * across the last 24 hours. Filtering (by time window, severity, root cause,
 * anomaly) happens in the page so the values update accordingly.
 */
export function generateIncidents(count = 60): MockIncident[] {
  const rand = mulberry32(hashSeed("historical-incidents"));
  const now = Date.now();
  const incidents: MockIncident[] = [];

  for (let i = 0; i < count; i++) {
    const level = 1 + Math.floor(rand() * 4);
    const severity = SEVERITY_BY_LEVEL[level];
    const rc = ROOT_CAUSES[Math.floor(rand() * ROOT_CAUSES.length)];
    // spread timestamps across the last 24h
    const minutesAgo = Math.floor(rand() * 24 * 60);
    const ts = new Date(now - minutesAgo * 60 * 1000);

    incidents.push({
      incident_id: `INC-${String(100000 + Math.floor(rand() * 899999))}`,
      timestamp: ts.toISOString(),
      severity,
      root_cause: rc.name,
      service: SERVICES[Math.floor(rand() * SERVICES.length)],
      tower: TOWERS[Math.floor(rand() * TOWERS.length)],
      anomaly: rand() > 0.55,
      error_count: Math.round(rand() * 200),
    });
  }

  return incidents.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );
}

// ── Mock investigation result ─────────────────────────────────────
export interface MockInvestigationInput {
  cpu_usage: number;
  memory_usage: number;
  error_count: number;
  latency_ms: number;
  incident_id?: string;
  description?: string;
  [key: string]: unknown;
}

export interface MockInvestigationResult {
  incident_id: string;
  severity: SeverityLabel;
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

/**
 * Build a deterministic-ish mock investigation result from the submitted
 * telemetry so the whole flow works without a backend.
 */
export function generateInvestigationResult(
  input: MockInvestigationInput,
): MockInvestigationResult {
  const incidentId = input.incident_id?.trim() || `INC-${Date.now().toString().slice(-6)}`;
  const rand = mulberry32(hashSeed(JSON.stringify(input)));

  // severity driven by the core metrics
  const score =
    (input.cpu_usage / 100) * 0.3 +
    (input.memory_usage / 100) * 0.3 +
    Math.min(input.error_count / 200, 1) * 0.2 +
    Math.min(input.latency_ms / 2000, 1) * 0.2;

  let severity: SeverityLabel = "P4 Low";
  if (score > 0.75) severity = "P1 Critical";
  else if (score > 0.55) severity = "P2 High";
  else if (score > 0.35) severity = "P3 Medium";

  const info = ROOT_CAUSES[Math.floor(rand() * ROOT_CAUSES.length)];
  const anomaly = score > 0.6;

  const similar = Array.from({ length: 3 }, () => {
    const rc = ROOT_CAUSES[Math.floor(rand() * ROOT_CAUSES.length)];
    return {
      incident_id: `INC-${String(100000 + Math.floor(rand() * 899999))}`,
      summary: `${rc.name} on ${SERVICES[Math.floor(rand() * SERVICES.length)]}`,
      root_cause: rc.name,
      resolution: rc.remediation,
      score: 0.7 + rand() * 0.29,
    };
  });

  const report_markdown = [
    `# Incident Report — ${incidentId}`,
    "",
    `**Severity:** ${severity}  `,
    `**Primary Root Cause:** ${info.name}  `,
    `**Anomaly:** ${anomaly ? "Detected" : "Normal"}`,
    "",
    "## Summary",
    info.description,
    "",
    "## Contributing Factors",
    ...info.contributingFactors.map((f) => `- ${f}`),
    "",
    "## Recommended Remediation",
    info.remediation,
    "",
    "## Observed Telemetry",
    `- CPU usage: ${input.cpu_usage}%`,
    `- Memory usage: ${input.memory_usage}%`,
    `- Error count: ${input.error_count}`,
    `- Latency: ${input.latency_ms} ms`,
  ].join("\n");

  return {
    incident_id: incidentId,
    severity,
    severity_confidence: 0.7 + rand() * 0.29,
    anomaly,
    anomaly_score: anomaly ? 0.6 + rand() * 0.39 : rand() * 0.4,
    root_cause: info.name,
    root_cause_confidence: 0.65 + rand() * 0.34,
    similar_incidents: similar,
    recommendations: [
      info.remediation,
      `Notify the on-call owner for the affected ${info.typicalSeverity} class incident.`,
      "Open a tracking ticket and attach the telemetry snapshot above.",
    ],
    report: info.description,
    report_markdown,
    processing_time_ms: Math.round(800 + rand() * 4000),
  };
}

export interface AnalysisFilters {
  circle: string;
  businessArea: string;
  date: string; // ISO yyyy-mm-dd
  hour: string; // HH:00
}

export interface SeverityPoint {
  time: string;        // hour label e.g. "08:00"
  severityLevel: number; // 1..4 (Y axis)
  severityLabel: SeverityLabel;
  rootCause: string;   // label rendered on the point
  info: RootCauseInfo;
  errorCount: number;
  anomaly: boolean;
}

export interface AnalysisResult {
  points: SeverityPoint[];
  summary: {
    totalIncidents: number;
    p1Count: number;
    anomalies: number;
    topRootCause: string;
  };
}

/**
 * Produce a deterministic severity-vs-time series for the selected filters.
 * The selected hour acts as the "peak" of activity for that window.
 */
export function generateAnalysis(filters: AnalysisFilters): AnalysisResult {
  const seedStr = `${filters.circle}|${filters.businessArea}|${filters.date}|${filters.hour}`;
  const rand = mulberry32(hashSeed(seedStr));

  const selectedHour = Number((filters.hour || "00:00").split(":")[0]);
  const points: SeverityPoint[] = [];

  let p1Count = 0;
  let anomalies = 0;
  const rcTally: Record<string, number> = {};

  for (let h = 0; h < 24; h++) {
    // distance from the selected (peak) hour shapes the severity curve
    const distance = Math.min(Math.abs(h - selectedHour), 24 - Math.abs(h - selectedHour));
    const proximity = 1 - distance / 12; // 1 at peak, ~0 far away

    const noise = rand();
    const intensity = Math.max(0, Math.min(1, proximity * 0.7 + noise * 0.5));

    let level = 1;
    if (intensity > 0.8) level = 4;
    else if (intensity > 0.6) level = 3;
    else if (intensity > 0.4) level = 2;
    else level = 1;

    const rcIndex = Math.floor(rand() * ROOT_CAUSES.length);
    const info = ROOT_CAUSES[rcIndex];
    const severityLabel = SEVERITY_BY_LEVEL[level];
    const errorCount = Math.round(intensity * 200 * rand());
    const anomaly = intensity > 0.65 && rand() > 0.4;

    if (level === 4) p1Count++;
    if (anomaly) anomalies++;
    rcTally[info.name] = (rcTally[info.name] ?? 0) + 1;

    points.push({
      time: HOURS[h],
      severityLevel: level,
      severityLabel,
      rootCause: info.name,
      info,
      errorCount,
      anomaly,
    });
  }

  const topRootCause =
    Object.entries(rcTally).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  return {
    points,
    summary: {
      totalIncidents: points.filter((p) => p.severityLevel >= 2).length,
      p1Count,
      anomalies,
      topRootCause,
    },
  };
}
