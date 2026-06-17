import { useMemo, useState } from "react";
import { useLocation } from "wouter";
import { Check, ChevronsUpDown, Search, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SeverityBadge } from "@/components/SeverityBadge";
import { cn } from "@/lib/utils";
import { ROOT_CAUSE_NAMES, generateIncidents } from "@/lib/mockData";

type TimeWindow = "24" | "8";

export default function Incidents() {
  const [, setLocation] = useLocation();
  const [severity, setSeverity] = useState<string>("all");
  const [rootCause, setRootCause] = useState<string>("");
  const [rcOpen, setRcOpen] = useState(false);
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("24");

  const allIncidents = useMemo(() => generateIncidents(60), []);

  const incidents = useMemo(() => {
    const cutoff = Date.now() - Number(timeWindow) * 60 * 60 * 1000;
    return allIncidents.filter((inc) => {
      if (new Date(inc.timestamp).getTime() < cutoff) return false;
      if (severity !== "all" && inc.severity !== severity) return false;
      if (rootCause && inc.root_cause !== rootCause) return false;
      if (anomalyOnly && !inc.anomaly) return false;
      return true;
    });
  }, [allIncidents, timeWindow, severity, rootCause, anomalyOnly]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">Historical Incidents</h2>
        <p className="text-muted-foreground">Search and filter past incident analyses.</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 bg-card p-4 rounded-lg border border-border/50">
        {/* Searchable root-cause dropdown */}
        <div className="relative flex-1">
          <Popover open={rcOpen} onOpenChange={setRcOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={rcOpen}
                className="w-full justify-between font-normal"
              >
                <span className="flex items-center gap-2 truncate">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  {rootCause || "Search root cause..."}
                </span>
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
              <Command>
                <CommandInput placeholder="Search root cause..." />
                <CommandList>
                  <CommandEmpty>No root cause found.</CommandEmpty>
                  <CommandGroup>
                    <CommandItem
                      value="__all__"
                      onSelect={() => {
                        setRootCause("");
                        setRcOpen(false);
                      }}
                    >
                      <Check className={cn("mr-2 h-4 w-4", rootCause === "" ? "opacity-100" : "opacity-0")} />
                      All root causes
                    </CommandItem>
                    {ROOT_CAUSE_NAMES.map((name) => (
                      <CommandItem
                        key={name}
                        value={name}
                        onSelect={() => {
                          setRootCause(name === rootCause ? "" : name);
                          setRcOpen(false);
                        }}
                      >
                        <Check className={cn("mr-2 h-4 w-4", rootCause === name ? "opacity-100" : "opacity-0")} />
                        {name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>

        <div className="w-full lg:w-48">
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

        {/* Anomaly time-window toggle */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-muted-foreground">Anomaly window</span>
            <ToggleGroup
              type="single"
              value={timeWindow}
              onValueChange={(v) => v && setTimeWindow(v as TimeWindow)}
              variant="outline"
              size="sm"
            >
              <ToggleGroupItem value="24" aria-label="Last 24 hours">24hr</ToggleGroupItem>
              <ToggleGroupItem value="8" aria-label="Last 8 hours">8hr</ToggleGroupItem>
            </ToggleGroup>
          </div>
          <div className="flex items-center space-x-2 pt-4">
            <Checkbox
              id="anomaly"
              checked={anomalyOnly}
              onCheckedChange={(c) => setAnomalyOnly(c as boolean)}
            />
            <label htmlFor="anomaly" className="text-sm font-medium leading-none">
              Anomalies Only
            </label>
          </div>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        Showing <span className="font-medium text-foreground">{incidents.length}</span> incidents from the last {timeWindow} hours.
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
            {incidents.length ? (
              incidents.map((inc) => (
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
