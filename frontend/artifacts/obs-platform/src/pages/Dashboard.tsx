import { useMemo, useState } from "react";
import { Link } from "wouter";
import { format } from "date-fns";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CalendarIcon,
  Play,
  ServerCrash,
  Sparkles,
} from "lucide-react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  LabelList,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/SeverityBadge";
import { cn } from "@/lib/utils";
import {
  BUSINESS_AREAS,
  CIRCLES,
  HOURS,
  SEVERITY_BY_LEVEL,
  generateAnalysis,
  type AnalysisFilters,
  type SeverityPoint,
} from "@/lib/mockData";

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const p: SeverityPoint = payload[0].payload;
  return (
    <div className="rounded-md border border-border/70 bg-popover text-popover-foreground shadow-md p-3 max-w-xs text-xs space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold text-sm">{p.rootCause}</span>
        <SeverityBadge severity={p.severityLabel} />
      </div>
      <p className="text-muted-foreground">{p.info.description}</p>
      <div>
        <span className="font-medium">Contributing factors: </span>
        {p.info.contributingFactors.join(", ")}
      </div>
      <div>
        <span className="font-medium">Remediation: </span>
        {p.info.remediation}
      </div>
      <div className="flex items-center gap-4 pt-1 font-mono text-muted-foreground">
        <span>{p.time}</span>
        <span>errors: {p.errorCount}</span>
        <span>{p.anomaly ? "anomaly" : "normal"}</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [circle, setCircle] = useState(CIRCLES[0]);
  const [businessArea, setBusinessArea] = useState(BUSINESS_AREAS[0]);
  const [date, setDate] = useState<Date>(new Date());
  const [hour, setHour] = useState(HOURS[9]);

  // committed filters drive the analysis (updated on "Run Analysis")
  const [applied, setApplied] = useState<AnalysisFilters>({
    circle: CIRCLES[0],
    businessArea: BUSINESS_AREAS[0],
    date: format(new Date(), "yyyy-MM-dd"),
    hour: HOURS[9],
  });

  const analysis = useMemo(() => generateAnalysis(applied), [applied]);

  const runAnalysis = () => {
    setApplied({
      circle,
      businessArea,
      date: format(date, "yyyy-MM-dd"),
      hour,
    });
  };

  const stats = [
    { title: "Active Incidents", value: analysis.summary.totalIncidents, icon: Activity, color: "text-blue-500" },
    { title: "P1 Critical", value: analysis.summary.p1Count, icon: ServerCrash, color: "text-red-500" },
    { title: "Anomalies Detected", value: analysis.summary.anomalies, icon: AlertTriangle, color: "text-orange-500" },
    { title: "Top Root Cause", value: analysis.summary.topRootCause, icon: Sparkles, color: "text-violet-500" },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">System Overview</h2>
          <p className="text-muted-foreground mt-1">Real-time observability and anomaly detection.</p>
        </div>
        <Link href="/investigate">
          <div className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow hover:bg-primary/90 h-10 px-4 py-2 cursor-pointer">
            Run Investigation
            <ArrowRight className="ml-2 w-4 h-4" />
          </div>
        </Link>
      </div>

      {/* ── Filters ─────────────────────────────────────────────── */}
      <Card className="border-border/50 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Analysis Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Geographical Circle</label>
            <Select value={circle} onValueChange={setCircle}>
              <SelectTrigger><SelectValue placeholder="Circle" /></SelectTrigger>
              <SelectContent>
                {CIRCLES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Business Area</label>
            <Select value={businessArea} onValueChange={setBusinessArea}>
              <SelectTrigger><SelectValue placeholder="Business Area" /></SelectTrigger>
              <SelectContent>
                {BUSINESS_AREAS.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Date</label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("w-full justify-start text-left font-normal", !date && "text-muted-foreground")}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {date ? format(date, "PP") : "Pick a date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={date}
                  onSelect={(d) => d && setDate(d)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Time (hourly)</label>
            <Select value={hour} onValueChange={setHour}>
              <SelectTrigger><SelectValue placeholder="Hour" /></SelectTrigger>
              <SelectContent className="max-h-64">
                {HOURS.map((h) => <SelectItem key={h} value={h}>{h}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <Button onClick={runAnalysis} className="font-medium">
            <Play className="mr-2 h-4 w-4" /> Run Analysis
          </Button>
        </CardContent>
      </Card>

      {/* ── Stat cards ──────────────────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <Card key={i} className="border-border/50 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono truncate">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Severity vs Time chart ──────────────────────────────── */}
      <Card className="border-border/50 shadow-sm">
        <CardHeader>
          <CardTitle>Severity Level vs Time</CardTitle>
          <p className="text-sm text-muted-foreground">
            {applied.circle} · {applied.businessArea} · {applied.date} · peak @ {applied.hour}.
            Each point is labelled with its root cause — hover for details.
          </p>
        </CardHeader>
        <CardContent>
          <div className="h-[420px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 30, right: 30, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
                <XAxis
                  dataKey="time"
                  name="Time"
                  tick={{ fontSize: 11 }}
                  interval={1}
                  angle={-35}
                  textAnchor="end"
                  height={50}
                />
                <YAxis
                  dataKey="severityLevel"
                  name="Severity"
                  type="number"
                  domain={[0, 5]}
                  ticks={[1, 2, 3, 4]}
                  tickFormatter={(v: number) => SEVERITY_BY_LEVEL[v] ?? ""}
                  width={90}
                  tick={{ fontSize: 11 }}
                />
                <ZAxis range={[120, 121]} />
                <RechartsTooltip content={<ChartTooltip />} cursor={{ strokeDasharray: "3 3" }} />
                <Scatter data={analysis.points} fill="hsl(var(--primary))">
                  <LabelList
                    dataKey="rootCause"
                    position="top"
                    style={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                  />
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
