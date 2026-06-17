import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { Layout } from "@/components/Layout";

import Dashboard from "@/pages/Dashboard";
import Investigation from "@/pages/Investigation";
import Results from "@/pages/Results";
import Incidents from "@/pages/Incidents";
import Predictions from "@/pages/Predictions";

const queryClient = new QueryClient();

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/investigate" component={Investigation} />
        <Route path="/results/:incidentId" component={Results} />
        <Route path="/incidents" component={Incidents} />
        <Route path="/predictions" component={Predictions} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster theme="system" richColors position="top-right" />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
