import React, { useState, useEffect } from 'react';
import { fetchTraffic, recommendDiversion, activateDiversion } from '../api';
import { Map, AlertOctagon, CheckCircle } from 'lucide-react';

export default function DiversionPanel() {
  const [segments, setSegments] = useState([]);
  const [selected, setSelected] = useState('');
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activated, setActivated] = useState(false);

  useEffect(() => {
    fetchTraffic().then(setSegments).catch(console.error);
  }, []);

  const handleRecommend = async () => {
    if (!selected) return;
    setLoading(true);
    setRec(null);
    setActivated(false);
    try {
      const data = await recommendDiversion(selected);
      setRec(data);
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!rec) return;
    setLoading(true);
    try {
      await activateDiversion(rec.diversion_id);
      setActivated(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel flex flex-col relative">
      <div className="px-4 py-3 border-b border-border bg-surfaceHover/50 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-warning text-sm">
          <AlertOctagon className="w-4 h-4" />
          INCIDENT DIVERSION
        </div>
      </div>
      
      <div className="p-4 flex-1 flex flex-col gap-4">
        <div className="flex gap-2">
          <select 
            className="input-field flex-1"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Select blocked road...</option>
            {segments.map(s => <option key={s.segment_id} value={s.segment_id}>{s.road} ({s.segment_id})</option>)}
          </select>
          <button 
            onClick={handleRecommend} 
            disabled={!selected || loading}
            className="btn btn-primary"
          >
            <Map className="w-4 h-4" />
            Find
          </button>
        </div>

        {rec && (
          <div className="bg-background rounded border border-border p-3 text-sm flex flex-col gap-3 animate-fade-in">
            <div className="text-xs text-muted">
              Alternative Path:
              <div className="text-text font-mono mt-1">{rec.diversion.path.join(' ➝ ')}</div>
            </div>
            
            <div className="grid grid-cols-2 gap-2 mt-1 border-t border-border/50 pt-2">
              <div className="text-xs text-muted flex flex-col">
                Delay Impact
                <span className="text-warning font-mono">+{rec.impact.additional_delay_min} min</span>
              </div>
              <div className="text-xs text-muted flex flex-col text-right">
                Distance
                <span className="text-text font-mono">{rec.diversion.distance_km} km</span>
              </div>
            </div>

            <button 
              onClick={handleActivate}
              disabled={loading || activated}
              className={`btn w-full mt-1 ${activated ? 'bg-success/20 text-success border-success/30' : 'btn-warning'}`}
            >
              {activated ? <><CheckCircle className="w-4 h-4" /> Rerouted</> : 'Activate Diversion'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
