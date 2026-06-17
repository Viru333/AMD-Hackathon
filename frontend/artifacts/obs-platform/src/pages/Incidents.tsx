import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Search, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Skeleton } from "@/components/ui/skeleton";

export default function Incidents() {
  const [, setLocation] = useLocation();
  const [severity, setSeverity] = useState<string>("all");
  const [rootCause, setRootCause] = useState<string>("");
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  
  // Debounce search
  const [debouncedRootCause, setDebouncedRootCause] = useState("");
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedRootCause(rootCause), 500);
    return () => clearTimeout(handler);
  }, [rootCause]);

  const { data, isLoading } = useQuery({
    queryKey: ["incidents", severity, debouncedRootCause, anomalyOnly],
    queryFn: ({ signal }) => api.getIncidents({ 
      limit: 50,
      severity: severity === "all" ? undefined : severity,
      root_cause: debouncedRootCause || undefined,
      anomaly_only: anomalyOnly || undefined
    }, signal),
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">Historical Incidents</h2>
        <p className="text-muted-foreground">Search and filter past incident analyses.</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 bg-card p-4 rounded-lg border border-border/50">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search root cause..." 
            className="pl-9"
            value={rootCause}
            onChange={(e) => {
              setRootCause(e.target.value);
            }}
          />
        </div>
        <div className="w-full sm:w-48">
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger>
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="P1 Critical">P1 Critical</SelectItem>
              <SelectItem value="P2 High">P2 High</SelectItem>
              <SelectItem value="P3 Medium">P3 Medium</SelectItem>
              <SelectItem value="P4 Low">P4 Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Checkbox 
            id="anomaly" 
            checked={anomalyOnly}
            onCheckedChange={(c) => setAnomalyOnly(c as boolean)} 
          />
          <label htmlFor="anomaly" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            Anomalies Only
          </label>
        </div>
      </div>

      <div className="border border-border/50 rounded-md bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Incident ID</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Service</TableHead>
              <TableHead>Root Cause</TableHead>
              <TableHead>Anomaly</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-6 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                </TableRow>
              ))
            ) : data?.incidents?.length ? (
              data.incidents.map((inc: any) => (
                <TableRow 
                  key={inc.incident_id} 
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => setLocation(`/results/${inc.incident_id}`)}
                >
                  <TableCell className="font-mono text-xs whitespace-nowrap text-muted-foreground">
                    {new Date(inc.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{inc.incident_id}</TableCell>
                  <TableCell>
                    <SeverityBadge severity={inc.severity} />
                  </TableCell>
                  <TableCell className="font-medium text-sm">
                    {inc.service}
                    <span className="text-xs text-muted-foreground block">{inc.tower}</span>
                  </TableCell>
                  <TableCell className="text-sm max-w-[300px] truncate">
                    {inc.root_cause}
                  </TableCell>
                  <TableCell>
                    {inc.anomaly ? <ShieldAlert className="w-4 h-4 text-orange-500" /> : <span className="text-muted-foreground">-</span>}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No incidents found matching filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}