import { cn } from "@/lib/utils";

interface SeverityBadgeProps {
  severity: string;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const getSeverityColors = (sev: string) => {
    if (sev.includes("P1")) return "bg-red-600/10 text-red-500 border-red-500/20";
    if (sev.includes("P2")) return "bg-orange-600/10 text-orange-500 border-orange-500/20";
    if (sev.includes("P3")) return "bg-yellow-600/10 text-yellow-500 border-yellow-500/20";
    if (sev.includes("P4")) return "bg-green-600/10 text-green-500 border-green-500/20";
    return "bg-slate-600/10 text-slate-500 border-slate-500/20";
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 font-mono uppercase tracking-wider",
        getSeverityColors(severity),
        className
      )}
    >
      {severity}
    </span>
  );
}