import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Activity, AlertTriangle, ArrowRight, ServerCrash, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/SeverityBadge";

export default function Dashboard() {
  const { data: incidentsData, isLoading } = useQuery({
    queryKey: ["incidents", "recent"],
    queryFn: ({ signal }) => api.getIncidents({ limit: 5 }, signal),
  });

  const { data: totalData } = useQuery({
    queryKey: ["incidents", "total"],
    queryFn: ({ signal }) => api.getIncidents({ limit: 1 }, signal),
  });

  const { data: p1Data } = useQuery({
    queryKey: ["incidents", "p1"],
    queryFn: ({ signal }) => api.getIncidents({ limit: 1, severity: "P1 Critical" }, signal),
  });

  const { data: anomalyData } = useQuery({
    queryKey: ["incidents", "anomaly"],
    queryFn: ({ signal }) => api.getIncidents({ limit: 1, anomaly_only: true }, signal),
  });

  const stats = [
    { title: "Total Incidents", value: totalData?.total ?? "-", icon: Activity, color: "text-blue-500" },
    { title: "P1 Critical", value: p1Data?.total ?? "-", icon: ServerCrash, color: "text-red-500" },
    { title: "Anomalies Detected", value: anomalyData?.total ?? "-", icon: AlertTriangle, color: "text-orange-500" },
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

      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat, i) => (
          <Card key={i} className="border-border/50 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-border/50 shadow-sm">
        <CardHeader>
          <CardTitle>Recent Incidents</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : incidentsData?.incidents?.length > 0 ? (
            <div className="space-y-4">
              {incidentsData.incidents.map((incident: any) => (
                <div key={incident.incident_id} className="flex items-center justify-between p-3 border border-border/50 rounded-lg hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-4">
                    <SeverityBadge severity={incident.severity} />
                    <div>
                      <p className="text-sm font-medium flex items-center gap-2">
                        {incident.service}
                        {incident.anomaly && <ShieldAlert className="w-3.5 h-3.5 text-orange-500" />}
                      </p>
                      <p className="text-xs text-muted-foreground font-mono">{new Date(incident.timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="hidden md:block">
                      <p className="text-muted-foreground text-xs">Root Cause</p>
                      <p className="font-medium truncate max-w-[200px]">{incident.root_cause}</p>
                    </div>
                    <Link href={`/results/${incident.incident_id}`}>
                      <div className="text-primary hover:underline text-sm font-medium cursor-pointer">
                        View Details
                      </div>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No recent incidents found.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}