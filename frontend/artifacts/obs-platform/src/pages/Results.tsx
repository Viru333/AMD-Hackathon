import { useEffect, useState } from "react";
import { useParams, Link } from "wouter";
import { ArrowLeft, Clock, Copy, Download, ShieldAlert, CheckCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import { InvestigationResult } from "@/lib/api";

const STEPS = ["Intake", "Anomaly", "Severity", "Root Cause", "Retrieval", "Runbooks", "Report"];

export default function Results() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [result, setResult] = useState<InvestigationResult | null>(null);

  useEffect(() => {
    // Try to load from session storage
    const stored = sessionStorage.getItem(`investigation_${incidentId}`);
    if (stored) {
      setResult(JSON.parse(stored));
    } else {
      // In a real app, fetch by ID if not in session
      // For this task, we assume it's there or handle graceful fallback
      toast.error("Investigation details not found in session");
    }
  }, [incidentId]);

  if (!result) {
    return <div className="p-8 text-center text-muted-foreground">Loading or not found...</div>;
  }

  const copyReport = () => {
    navigator.clipboard.writeText(result.report_markdown);
    toast.success("Report copied to clipboard");
  };

  const downloadReport = () => {
    const blob = new Blob([result.report_markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `incident-${result.incident_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/incidents">
          <Button variant="outline" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Investigation: {result.incident_id}</h2>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
            <Clock className="w-4 h-4" />
            Processed in {(result.processing_time_ms / 1000).toFixed(2)}s
          </div>
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" size="sm" onClick={copyReport}>
            <Copy className="w-4 h-4 mr-2" /> Copy
          </Button>
          <Button variant="outline" size="sm" onClick={downloadReport}>
            <Download className="w-4 h-4 mr-2" /> Download
          </Button>
        </div>
      </div>

      <Card className="border-border/50 bg-muted/20">
        <CardContent className="pt-6">
          <WorkflowStepper steps={STEPS} currentStep={STEPS.length} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Severity</CardTitle>
          </CardHeader>
          <CardContent>
            <SeverityBadge severity={result.severity} className="text-lg px-3 py-1 mb-4" />
            <ConfidenceBar confidence={result.severity_confidence} label="Confidence Score" />
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Anomaly Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 mb-4">
              {result.anomaly ? (
                <ShieldAlert className="w-8 h-8 text-orange-500" />
              ) : (
                <CheckCircle className="w-8 h-8 text-green-500" />
              )}
              <span className="text-xl font-bold">{result.anomaly ? "Detected" : "Normal"}</span>
            </div>
            <ConfidenceBar confidence={result.anomaly_score} label="Anomaly Score" />
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Primary Root Cause</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold mb-4 leading-tight">{result.root_cause}</div>
            <ConfidenceBar confidence={result.root_cause_confidence} label="Confidence Score" />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-border/50 md:col-span-1 h-fit">
          <CardHeader>
            <CardTitle>Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {result.recommendations.map((rec, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="bg-primary/20 text-primary w-5 h-5 rounded-full flex items-center justify-center text-xs shrink-0 font-mono mt-0.5">{i + 1}</span>
                  <span className="leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card className="border-border/50 md:col-span-1 h-fit">
          <CardHeader>
            <CardTitle>Similar Historical Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {result.similar_incidents.map(inc => (
                <div key={inc.incident_id} className="border-b border-border/50 pb-3 last:border-0 last:pb-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-mono text-xs text-primary">{inc.incident_id}</span>
                    <span className="text-xs font-mono text-muted-foreground">Match: {Math.round(inc.score * 100)}%</span>
                  </div>
                  <p className="text-sm font-medium">{inc.summary}</p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-1">Resolution: {inc.resolution}</p>
                </div>
              ))}
              {result.similar_incidents.length === 0 && (
                <p className="text-sm text-muted-foreground">No highly similar incidents found.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Detailed Analysis Report</CardTitle>
        </CardHeader>
        <CardContent>
          <article className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {result.report_markdown}
            </ReactMarkdown>
          </article>
        </CardContent>
      </Card>
    </div>
  );
}