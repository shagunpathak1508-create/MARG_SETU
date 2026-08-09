import React, { useState, useEffect } from 'react';
import { fetchJunctions, optimizeSignal, activateSignal, fetchSignals } from '../api';
import { Settings2, Cpu, CheckCircle } from 'lucide-react';

export default function SignalOptimizationPanel({ onUpdate }) {
  const [junctions, setJunctions] = useState([]);
  const [selected, setSelected] = useState('');
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activated, setActivated] = useState(false);

  useEffect(() => {
    fetchJunctions().then(setJunctions).catch(console.error);
  }, []);

  const handleOptimize = async () => {
    if (!selected) return;
    setLoading(true);
    setRec(null);
    setActivated(false);
    try {
      const data = await optimizeSignal(selected);
      setRec(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!selected || !rec) return;
    setLoading(true);
    try {
      await activateSignal(selected);
      setActivated(true);
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel flex flex-col relative">
      <div className="px-4 py-3 border-b border-border bg-surfaceHover/50 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-primary text-sm">
          <Settings2 className="w-4 h-4" />
          SIGNAL OPTIMIZATION
        </div>
        <div className="badge border-primary/30 text-primary bg-primary/10">Prototype</div>
      </div>
      
      <div className="p-4 flex-1 flex flex-col gap-4">
        <div className="flex gap-2">
          <select 
            className="input-field flex-1"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Select a junction...</option>
            {junctions.map(j => <option key={j.junction_id} value={j.junction_id}>{j.name} ({j.junction_id})</option>)}
          </select>
          <button 
            onClick={handleOptimize} 
            disabled={!selected || loading}
            className="btn btn-primary"
          >
            <Cpu className="w-4 h-4" />
            Analyze
          </button>
        </div>

        {loading && !rec && !activated && (
          <div className="text-muted text-sm flex items-center gap-2 justify-center py-4">
            <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></span>
            Computing optimal phase timings...
          </div>
        )}

        {rec && (
          <div className="bg-background rounded border border-border p-3 text-sm flex flex-col gap-3 animate-fade-in">
            <div className="text-muted italic border-l-2 border-primary/50 pl-2">
              "{rec.explanation}"
            </div>
            
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="text-xs text-muted">Mode: <span className="text-primary font-mono">{rec.recommendation.mode}</span></div>
              <div className="text-xs text-muted text-right">Cycle: <span className="font-mono text-text">{rec.recommendation.total_cycle_sec}s</span></div>
            </div>

            <button 
              onClick={handleActivate}
              disabled={loading || activated}
              className={`btn w-full mt-2 ${activated ? 'bg-success/20 text-success border-success/30' : 'btn-success'}`}
            >
              {activated ? <><CheckCircle className="w-4 h-4" /> Activated</> : 'Activate Timings'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
