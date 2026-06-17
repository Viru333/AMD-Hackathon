import { useState, useEffect, useRef } from "react";
import { ShieldAlert, CheckCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";

export default function Predictions() {
  const [metrics, setMetrics] = useState({
    cpu_usage: 85,
    memory_usage: 90,
    error_count: 150,
    latency_ms: 1200,
    disk_usage: 50,
  });

  const [severityResult, setSeverityResult] = useState<any>(null);
  const [anomalyResult, setAnomalyResult] = useState<any>(null);
  const [rootCauseResult, setRootCauseResult] = useState<any>(null);
  
  const [loading, setLoading] = useState({ sev: false, anom: false, rc: false });

  const abortControllers = useRef({
    sev: new AbortController(),
    anom: new AbortController(),
    rc: new AbortController(),
  });

  const runPrediction = async (type: 'sev' | 'anom' | 'rc') => {
    setLoading(prev => ({ ...prev, [type]: true }));
    
    // Abort previous
    abortControllers.current[type].abort();
    abortControllers.current[type] = new AbortController();
    
    try {
      const data = { ...metrics, service: "live-test" };
      let res;
      if (type === 'sev') {
        res = await api.predictSeverity(data, abortControllers.current.sev.signal);
        setSeverityResult(res);
      } else if (type === 'anom') {
        res = await api.predictAnomaly(data, abortControllers.current.anom.signal);
        setAnomalyResult(res);
      } else {
        res = await api.predictRootCause(data, abortControllers.current.rc.signal);
        setRootCauseResult(res);
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error("Prediction error", e);
      }
    } finally {
      setLoading(prev => ({ ...prev, [type]: false }));
    }
  };

  // Debounced auto-run on metric change
  useEffect(() => {
    const timer = setTimeout(() => {
      runPrediction('sev');
      runPrediction('anom');
      runPrediction('rc');
    }, 600);
    return () => clearTimeout(timer);
  }, [metrics]);

  const handleChange = (k: string, v: string) => {
    setMetrics(prev => ({ ...prev, [k]: Number(v) || 0 }));
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">Live Predictions</h2>
        <p className="text-muted-foreground">Adjust telemetry below to see real-time ML predictions.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1 border-border/50 h-fit">
          <CardHeader>
            <CardTitle>Live Telemetry</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(metrics).map(([k, v]) => (
              <div key={k} className="space-y-1.5">
                <Label className="capitalize text-xs">{k.replace('_', ' ')}</Label>
                <Input 
                  type="number" 
                  value={v} 
                  onChange={(e) => handleChange(k, e.target.value)} 
                  className="font-mono h-8"
                />
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="lg:col-span-3">
          <Tabs defaultValue="severity" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="severity">Severity</TabsTrigger>
              <TabsTrigger value="anomaly">Anomaly Detection</TabsTrigger>
              <TabsTrigger value="rootcause">Root Cause</TabsTrigger>
            </TabsList>
            
            <TabsContent value="severity" className="mt-4">
              <Card className="border-border/50 min-h-[300px]">
                <CardHeader>
                  <CardTitle className="flex justify-between items-center">
                    Severity Prediction
                    {loading.sev && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {severityResult ? (
                    <div className="space-y-6">
                      <div>
                        <SeverityBadge severity={severityResult.severity} className="text-xl px-4 py-2" />
                        <div className="mt-4">
                          <ConfidenceBar confidence={severityResult.confidence} label="Top Prediction Confidence" />
                        </div>
                      </div>
                      
                      {severityResult.all_probabilities && (
                        <div className="space-y-3 pt-4 border-t border-border/50">
                          <h4 className="text-sm font-semibold text-muted-foreground">All Probabilities</h4>
                          {Object.entries(severityResult.all_probabilities).map(([sev, prob]: any) => (
                            <div key={sev} className="flex items-center gap-4 text-sm">
                              <span className="w-24 font-mono">{sev}</span>
                              <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                                <div className="h-full bg-primary" style={{ width: `${prob * 100}%` }} />
                              </div>
                              <span className="w-12 text-right font-mono text-muted-foreground">{(prob * 100).toFixed(1)}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : <div className="text-muted-foreground">Waiting for data...</div>}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="anomaly" className="mt-4">
              <Card className="border-border/50 min-h-[300px]">
                <CardHeader>
                  <CardTitle className="flex justify-between items-center">
                    Anomaly Detection
                    {loading.anom && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {anomalyResult ? (
                    <div className="space-y-6">
                      <div className="flex items-center gap-4">
                        {anomalyResult.anomaly ? (
                          <ShieldAlert className="w-12 h-12 text-orange-500" />
                        ) : (
                          <CheckCircle className="w-12 h-12 text-green-500" />
                        )}
                        <div>
                          <div className="text-2xl font-bold">{anomalyResult.anomaly ? "ANOMALY DETECTED" : "SYSTEM NORMAL"}</div>
                          <div className="text-sm text-muted-foreground">Score: {anomalyResult.score.toFixed(4)}</div>
                        </div>
                      </div>
                      <div className="pt-4">
                        <ConfidenceBar confidence={anomalyResult.score} label="Anomaly Score (Higher is more anomalous)" />
                      </div>
                    </div>
                  ) : <div className="text-muted-foreground">Waiting for data...</div>}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="rootcause" className="mt-4">
              <Card className="border-border/50 min-h-[300px]">
                <CardHeader>
                  <CardTitle className="flex justify-between items-center">
                    Root Cause Prediction
                    {loading.rc && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {rootCauseResult ? (
                    <div className="space-y-6">
                      <div>
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Primary Cause</h4>
                        <div className="text-xl font-bold p-3 bg-secondary/30 rounded-md border border-border/50">
                          {rootCauseResult.root_cause}
                        </div>
                        <div className="mt-4">
                          <ConfidenceBar confidence={rootCauseResult.confidence} label="Confidence" />
                        </div>
                      </div>

                      {rootCauseResult.top3 && (
                        <div className="space-y-3 pt-4 border-t border-border/50">
                          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Top Candidates</h4>
                          {rootCauseResult.top3.map((cand: any, idx: number) => (
                            <div key={idx} className="bg-card border border-border/50 p-3 rounded-md">
                              <div className="flex justify-between items-center mb-2">
                                <span className="font-medium text-sm">{cand.root_cause}</span>
                                <span className="font-mono text-xs text-muted-foreground">{(cand.confidence * 100).toFixed(1)}%</span>
                              </div>
                              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                                <div className="h-full bg-primary opacity-70" style={{ width: `${cand.confidence * 100}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : <div className="text-muted-foreground">Waiting for data...</div>}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}