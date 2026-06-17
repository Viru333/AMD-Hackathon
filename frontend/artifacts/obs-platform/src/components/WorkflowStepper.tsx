import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface WorkflowStepperProps {
  steps: string[];
  currentStep: number;
  className?: string;
}

export function WorkflowStepper({ steps, currentStep, className }: WorkflowStepperProps) {
  return (
    <div className={cn("w-full overflow-x-auto pb-4", className)}>
      <div className="flex items-center min-w-max px-2">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isPending = index > currentStep;

          return (
            <div key={step} className="flex items-center">
              <div className="flex flex-col items-center gap-2 relative">
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors duration-300 z-10 bg-background",
                    isCompleted
                      ? "border-primary text-primary"
                      : isCurrent
                      ? "border-primary text-primary"
                      : "border-muted text-muted-foreground"
                  )}
                >
                  {isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span className="text-xs font-mono">{index + 1}</span>
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-mono absolute top-10 whitespace-nowrap",
                    isCompleted || isCurrent ? "text-foreground font-medium" : "text-muted-foreground"
                  )}
                >
                  {step}
                </span>
              </div>

              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "w-12 sm:w-24 h-[2px] mx-2 transition-colors duration-300",
                    isCompleted ? "bg-primary" : "bg-muted"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}