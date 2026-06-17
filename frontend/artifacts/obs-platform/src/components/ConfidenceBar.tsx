import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

interface ConfidenceBarProps {
  confidence: number; // 0 to 1
  label?: string;
  className?: string;
}

export function ConfidenceBar({ confidence, label, className }: ConfidenceBarProps) {
  const percentage = Math.round(confidence * 100);
  
  const getColor = (val: number) => {
    if (val >= 0.8) return "bg-green-500";
    if (val >= 0.5) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className={cn("flex flex-col gap-1.5 w-full", className)}>
      <div className="flex justify-between items-center text-xs text-muted-foreground font-mono">
        <span>{label || "Confidence"}</span>
        <span>{percentage}%</span>
      </div>
      <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
        <div 
          className={cn("h-full transition-all duration-500 ease-out", getColor(confidence))} 
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}