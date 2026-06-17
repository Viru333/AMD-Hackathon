import { useQuery } from "@tanstack/react-query";
import { Activity, ServerCrash } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export function HealthStatus({ className }: { className?: string }) {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.getHealth(signal),
    refetchInterval: 30000,
  });

  const isHealthy = data?.status === "ok";

  return (
    <div className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm font-mono", 
      isLoading ? "bg-muted text-muted-foreground border-border" :
      isError || !isHealthy ? "bg-destructive/10 text-destructive border-destructive/20" : 
      "bg-green-500/10 text-green-500 border-green-500/20",
      className
    )}>
      {isLoading ? (
        <Activity className="w-4 h-4 animate-pulse" />
      ) : isError || !isHealthy ? (
        <ServerCrash className="w-4 h-4" />
      ) : (
        <Activity className="w-4 h-4" />
      )}
      <span>{isLoading ? "Checking..." : isError || !isHealthy ? "System Degraded" : "All Systems Operational"}</span>
    </div>
  );
}