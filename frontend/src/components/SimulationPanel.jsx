import React, { useState } from 'react';
import { runSimulation } from '../api';
import { TestTube, Play } from 'lucide-react';

export default function SimulationPanel() {
  const [params, setParams] = useState({ traffic_multiplier: 1.0, incident_severity: 1.0 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const data = await runSimulation(params);
      setResult(data);
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel flex flex-col relative">
      <div className="px-4 py-3 border-b border-border bg-surfaceHover/50 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-primary text-sm">
          <TestTube className="w-4 h-4" />
          SCENARIO SIMULATION
        </div>
        <div className="badge border-muted text-muted">What-If Engine</div>
      </div>
      
      <div className="p-4 flex-1 flex flex-col gap-4">
        <div className="space-y-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted flex justify-between">
              Traffic Volume Multiplier <span>{params.traffic_multiplier}x</span>
            </label>
            <input 
              type="range" min="0.1" max="3.0" step="0.1" 
              value={params.traffic_multiplier} 
              onChange={e => setParams({...params, traffic_multiplier: parseFloat(e.target.value)})}
              className="w-full accent-primary" 
            />
          </div>
          
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted flex justify-between">
              Incident Severity <span>{params.incident_severity}x</span>
            </label>
            <input 
              type="range" min="1.0" max="5.0" step="0.5" 
              value={params.incident_severity} 
              onChange={e => setParams({...params, incident_severity: parseFloat(e.target.value)})}
              className="w-full accent-danger" 
            />
          </div>

          <button onClick={handleSimulate} disabled={loading} className="btn btn-primary w-full text-sm">
            <Play className="w-4 h-4" /> Run Simulation
          </button>
        </div>

        {result && (
          <div className="bg-background rounded border border-border p-3 text-sm animate-slide-up mt-1">
            <div className="text-xs text-muted mb-2 uppercase tracking-wider font-semibold border-b border-border/50 pb-1">Before ➝ After Optimization</div>
            
            <div className="grid grid-cols-2 gap-x-2 gap-y-3">
              <div className="flex flex-col">
                <span className="text-[10px] text-muted">Congestion</span>
                <div className="flex items-end gap-1">
                  <span className="text-xs line-through text-muted/70">{result.before.avg_congestion_pct}%</span>
                  <span className="font-mono text-text">{result.after.avg_congestion_pct}%</span>
                </div>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-muted">Wait Time</span>
                <div className="flex items-end gap-1">
                  <span className="text-xs line-through text-muted/70">{result.before.avg_waiting_time_sec}s</span>
                  <span className="font-mono text-success">{result.after.avg_waiting_time_sec}s</span>
                </div>
              </div>
              <div className="flex flex-col col-span-2">
                <span className="text-[10px] text-muted">Queue Length (Vehicles)</span>
                <div className="flex items-end gap-1">
                  <span className="text-xs line-through text-muted/70">{result.before.avg_queue_length}</span>
                  <span className="font-mono text-primary">{result.after.avg_queue_length}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
