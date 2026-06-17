import { Link, useLocation } from "wouter";
import { 
  Activity, 
  AlertTriangle, 
  BarChart3, 
  History, 
  LayoutDashboard, 
  Moon, 
  Sun,
  Terminal
} from "lucide-react";
import { useEffect, useState } from "react";
import { HealthStatus } from "./HealthStatus";
import { cn } from "@/lib/utils";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const isDarkStored = localStorage.getItem("theme") !== "light";
    setIsDark(isDarkStored);
    if (isDarkStored) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = !isDark;
    setIsDark(newTheme);
    localStorage.setItem("theme", newTheme ? "dark" : "light");
    if (newTheme) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/investigate", label: "New Investigation", icon: Activity },
    { href: "/incidents", label: "Historical Incidents", icon: History },
    { href: "/predictions", label: "Live Predictions", icon: BarChart3 },
  ];

  return (
    <div className="flex min-h-screen bg-background text-foreground font-sans">
      <aside className="w-64 border-r border-border bg-sidebar flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <Terminal className="w-6 h-6 text-primary mr-2" />
          <span className="font-bold tracking-tight">AGENT<span className="text-primary">OBS</span></span>
        </div>
        
        <div className="p-4 flex-1">
          <div className="space-y-1 mb-8">
            <p className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Navigation</p>
            {navItems.map((item) => {
              const isActive = location === item.href;
              return (
                <Link key={item.href} href={item.href}>
                  <div className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors cursor-pointer",
                    isActive 
                      ? "bg-primary/10 text-primary font-medium" 
                      : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}>
                    <item.icon className="w-4 h-4" />
                    {item.label}
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="p-4 border-t border-border">
          <HealthStatus className="mb-4 w-full justify-center" />
          <button 
            onClick={toggleTheme}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full px-2 py-1"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{isDark ? "Light Mode" : "Dark Mode"}</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-border flex items-center justify-between px-8 bg-card">
          <h1 className="text-lg font-semibold">
            {navItems.find(item => item.href === location)?.label || "Investigation Details"}
          </h1>
          <div className="flex items-center gap-4">
            {/* Contextual actions could go here */}
          </div>
        </header>
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
}