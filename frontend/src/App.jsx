import { useState, useEffect } from 'react';
import { Clock, Activity, AlertTriangle, Route } from 'lucide-react';
import { fetchComparison } from './api';

import KPIGrid from './components/KPIGrid';
import LiveTrafficPanel from './components/LiveTrafficPanel';
import NetworkMap from './components/NetworkMap';
import SignalOptimizationPanel from './components/SignalOptimizationPanel';
import EmergencyPanel from './components/EmergencyPanel';
import DiversionPanel from './components/DiversionPanel';
import SimulationPanel from './components/SimulationPanel';

function App() {
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const loadMetrics = async () => {
    try {
      const data = await fetchComparison();
      setMetrics(data.before);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Header */}
      <header className="h-14 border-b border-border bg-surface flex items-center justify-between px-6 shrink-0 z-10 relative">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-transparent pointer-events-none"></div>
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-primary" />
          <h1 className="text-lg font-semibold tracking-wide flex items-center gap-2">
            MARGSETU <span className="text-muted font-normal">|</span> SMART CITY COMMAND
          </h1>
          <div className="ml-4 px-2 py-0.5 rounded-full bg-danger/10 border border-danger/30 text-danger text-xs font-medium flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse"></span>
            LIVE ANALYTICS
          </div>
        </div>
        <div className="flex items-center gap-6 text-sm text-muted">
          <div className="flex items-center gap-2 text-warning">
            <AlertTriangle className="w-4 h-4" />
            <span>Prototype Signal Execution Mode</span>
          </div>
          <div className="flex items-center gap-2 font-mono text-text">
            <Clock className="w-4 h-4 text-primary" />
            {time}
          </div>
        </div>
      </header>

      {/* Main Content Scrollable Area */}
      <main className="flex-1 overflow-auto p-4 md:p-6 space-y-6 bg-gradient-to-br from-background to-[#0d0f17]">
        {/* Top KPI Strip */}
        <KPIGrid metrics={metrics} />

        {/* 3-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Col: Monitoring & Map */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <div className="panel flex-1 min-h-[500px] flex flex-col">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-surfaceHover/50">
                <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                  <Route className="w-4 h-4" />
                  LIVE TRAFFIC NETWORK
                </div>
                <div className="flex gap-2">
                  <span className="badge border-success/30 text-success bg-success/10">Low</span>
                  <span className="badge border-warning/30 text-warning bg-warning/10">Mod</span>
                  <span className="badge border-danger/30 text-danger bg-danger/10">High</span>
                </div>
              </div>
              <div className="flex-1 relative bg-[#0a0c13]">
                <NetworkMap />
              </div>
            </div>

            <div className="panel h-[400px] flex flex-col">
               <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-surfaceHover/50">
                 <div className="text-sm font-semibold text-primary">TRAFFIC MONITORING</div>
                 <div className="text-xs text-muted">Updates every 5s</div>
               </div>
               <div className="flex-1 overflow-auto p-4">
                  <LiveTrafficPanel />
               </div>
            </div>
          </div>

          {/* Right Col: Operations Panels */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <SignalOptimizationPanel onUpdate={loadMetrics} />
            <EmergencyPanel />
            <DiversionPanel />
            <SimulationPanel />
          </div>

        </div>
      </main>
    </div>
  );
}

export default App;
