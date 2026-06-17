import { useState } from "react";
import { useLocation } from "wouter";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { WorkflowStepper } from "@/components/WorkflowStepper";

const formSchema = z.object({
  cpu_usage: z.coerce.number().min(0).max(100),
  memory_usage: z.coerce.number().min(0).max(100),
  error_count: z.coerce.number().min(0),
  latency_ms: z.coerce.number().min(0),
  disk_usage: z.coerce.number().min(0).max(100).optional().default(50),
  warn_count: z.coerce.number().min(0).optional().default(20),
  alert_volume: z.coerce.number().min(0).optional().default(3),
  duration_min: z.coerce.number().min(0).optional().default(30),
  impacted_services: z.coerce.number().min(0).optional().default(1),
  error_rate: z.coerce.number().min(0).max(1).optional().default(0.5),
  net_in_mbps: z.coerce.number().min(0).optional().default(100),
  net_out_mbps: z.coerce.number().min(0).optional().default(80),
  request_rate: z.coerce.number().min(0).optional().default(500),
  gc_pause_ms: z.coerce.number().min(0).optional().default(20),
  thread_count: z.coerce.number().min(0).optional().default(50),
  tower: z.string().optional().default("Application"),
  service: z.string().optional().default("api-gateway"),
  incident_id: z.string().optional(),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

const STEPS = ["Intake", "Anomaly", "Severity", "Root Cause", "Retrieval", "Runbooks", "Report"];

export default function Investigation() {
  const [, setLocation] = useLocation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      cpu_usage: 85,
      memory_usage: 90,
      error_count: 150,
      latency_ms: 1200,
      disk_usage: 50,
      warn_count: 20,
      alert_volume: 3,
      duration_min: 30,
      impacted_services: 1,
      error_rate: 0.5,
      net_in_mbps: 100,
      net_out_mbps: 80,
      request_rate: 500,
      gc_pause_ms: 20,
      thread_count: 50,
      tower: "Application",
      service: "api-gateway",
    },
  });

  async function onSubmit(data: FormValues) {
    setIsSubmitting(true);
    setCurrentStep(0);
    
    // Simulate steps progression for UI feel
    const interval = setInterval(() => {
      setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
    }, 800);

    try {
      const result = await api.investigate(data);
      clearInterval(interval);
      setCurrentStep(STEPS.length);
      toast.success("Investigation complete");
      
      // Store result in sessionStorage to pass it
      sessionStorage.setItem(`investigation_${result.incident_id}`, JSON.stringify(result));
      
      setTimeout(() => {
        setLocation(`/results/${result.incident_id}`);
      }, 500);
    } catch (error: any) {
      clearInterval(interval);
      toast.error(`Investigation failed: ${error.message}`);
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">New Investigation</h2>
        <p className="text-muted-foreground">Submit telemetry data for agentic root cause analysis.</p>
      </div>

      {isSubmitting && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="pt-6">
            <WorkflowStepper steps={STEPS} currentStep={currentStep} />
            <div className="text-center mt-4 text-sm font-mono text-muted-foreground animate-pulse">
              Agent is analyzing telemetry...
            </div>
          </CardContent>
        </Card>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Required Telemetry</CardTitle>
              <CardDescription>Core metrics required for initial triage.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField control={form.control} name="cpu_usage" render={({ field }) => (
                <FormItem>
                  <FormLabel>CPU Usage (%)</FormLabel>
                  <FormControl><Input type="number" step="0.1" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="memory_usage" render={({ field }) => (
                <FormItem>
                  <FormLabel>Memory Usage (%)</FormLabel>
                  <FormControl><Input type="number" step="0.1" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="error_count" render={({ field }) => (
                <FormItem>
                  <FormLabel>Error Count</FormLabel>
                  <FormControl><Input type="number" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="latency_ms" render={({ field }) => (
                <FormItem>
                  <FormLabel>Latency (ms)</FormLabel>
                  <FormControl><Input type="number" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            </CardContent>
          </Card>

          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Extended Context</CardTitle>
              <CardDescription>Additional metrics improve root cause accuracy.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {['tower', 'service', 'incident_id'].map(name => (
                <FormField key={name} control={form.control} name={name as any} render={({ field }) => (
                  <FormItem>
                    <FormLabel className="capitalize">{name.replace('_', ' ')}</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              ))}
              {['disk_usage', 'warn_count', 'alert_volume', 'duration_min', 'impacted_services', 'error_rate', 'net_in_mbps', 'net_out_mbps', 'request_rate', 'gc_pause_ms', 'thread_count'].map(name => (
                <FormField key={name} control={form.control} name={name as any} render={({ field }) => (
                  <FormItem>
                    <FormLabel className="capitalize">{name.replace(/_/g, ' ')}</FormLabel>
                    <FormControl><Input type="number" step="0.1" {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              ))}
              <div className="col-span-1 md:col-span-3">
                <FormField control={form.control} name="description" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (Optional)</FormLabel>
                    <FormControl><Input placeholder="Brief description of the incident..." {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button type="submit" size="lg" disabled={isSubmitting} className="font-mono uppercase tracking-wide">
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isSubmitting ? "Processing..." : "Run Investigation"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}