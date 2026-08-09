import React, { useState, useEffect } from 'react';
import { fetchJunctions, createEmergencyCorridor, activateEmergencyCorridor, advanceEmergencyCorridor } from '../api';
import { Siren, Navigation, Play, CheckCircle } from 'lucide-react';

export default function EmergencyPanel() {
  const [junctions, setJunctions] = useState([]);
  const [form, setForm] = useState({ vehicle_type: 'ambulance', origin: '', destination: '', priority_level: 'high' });
  const [corridor, setCorridor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(false);

  useEffect(() => {
    fetchJunctions().then(setJunctions).catch(console.error);
  }, []);

  const handleCreate = async () => {
    if (!form.origin || !form.destination) return;
    setLoading(true);
    setCorridor(null);
    setActive(false);
    try {
      const data = await createEmergencyCorridor(form);
      setCorridor(data);
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!corridor) return;
    setLoading(true);
    try {
      await activateEmergencyCorridor(corridor.id);
      setActive(true);
      // Start auto-advance simulation
      let currentPos = 0;
      const pathLen = corridor.path.length;
      
      const simInterval = setInterval(async () => {
        if (currentPos >= pathLen - 1) {
          clearInterval(simInterval);
          return;
        }
        try {
          const updated = await advanceEmergencyCorridor(corridor.id);
          setCorridor(updated);
          currentPos = updated.current_position_index;
          if (updated.status === 'COMPLETED') clearInterval(simInterval);
        } catch (e) {
          console.error(e);
          clearInterval(simInterval);
        }
      }, 2000); // Advance every 2 seconds for visual effect
      
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel flex flex-col relative">
      <div className="px-4 py-3 border-b border-border bg-surfaceHover/50 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-danger text-sm">
          <Siren className="w-4 h-4" />
          EMERGENCY DISPATCH
        </div>
        <div className="badge border-danger/30 text-danger bg-danger/10 animate-pulse">Priority Route</div>
      </div>
      
      <div className="p-4 flex-1 flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          <select className="input-field col-span-2" value={form.vehicle_type} onChange={e => setForm({...form, vehicle_type: e.target.value})}>
            <option value="ambulance">Ambulance</option>
            <option value="fire">Fire Engine</option>
            <option value="police">Police Interceptor</option>
          </select>
          <select className="input-field" value={form.origin} onChange={e => setForm({...form, origin: e.target.value})}>
            <option value="">Origin...</option>
            {junctions.map(j => <option key={j.junction_id} value={j.junction_id}>{j.name}</option>)}
          </select>
          <select className="input-field" value={form.destination} onChange={e => setForm({...form, destination: e.target.value})}>
            <option value="">Destination...</option>
            {junctions.map(j => <option key={j.junction_id} value={j.junction_id}>{j.name}</option>)}
          </select>
        </div>
        
        <button onClick={handleCreate} disabled={!form.origin || !form.destination || loading} className="btn btn-danger w-full">
          <Navigation className="w-4 h-4" /> Request Corridor
        </button>

        {corridor && !active && (
          <div className="bg-background rounded border border-border p-3 text-sm animate-slide-up mt-2">
            <div className="flex justify-between items-center mb-2">
              <span className="text-muted text-xs font-mono">{corridor.id}</span>
              <span className="text-success font-bold text-xs">{corridor.time_saved_min} min saved</span>
            </div>
            <div className="text-xs text-muted mb-3 break-words">Path: {corridor.path.join(' ➝ ')}</div>
            <button onClick={handleActivate} className="btn bg-danger/20 text-danger border border-danger/40 hover:bg-danger/30 w-full text-xs">
              <Play className="w-3 h-3" /> Activate Preemption
            </button>
          </div>
        )}

        {active && corridor && (
          <div className="bg-background rounded border border-border p-3 text-sm animate-fade-in mt-2">
             <div className="flex justify-between items-center mb-3">
               <span className="text-xs text-primary font-mono flex items-center gap-2">
                 <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span> ACTIVE
               </span>
               <span className="text-xs font-mono">{corridor.status}</span>
             </div>
             
             <div className="space-y-2">
               {corridor.junctions.map((j, i) => {
                 let color = "text-muted";
                 let bg = "bg-surface";
                 if (j.status === 'CLEARED') { color = "text-success"; bg = "bg-success/10 border-success/20"; }
                 if (j.status === 'ACTIVE') { color = "text-danger font-bold"; bg = "bg-danger/10 border-danger/30"; }
                 if (j.status === 'PREPARING') { color = "text-warning"; bg = "bg-warning/10 border-warning/20"; }
                 
                 return (
                   <div key={i} className={`text-xs p-1.5 rounded border border-transparent flex justify-between transition-all duration-300 ${bg}`}>
                     <span className={color}>{j.junction_id} - {j.junction_name}</span>
                     <span className={`font-mono ${color}`}>{j.status}</span>
                   </div>
                 );
               })}
             </div>
             
             {corridor.status === 'COMPLETED' && (
               <div className="mt-3 text-success text-xs font-bold flex items-center justify-center gap-1">
                 <CheckCircle className="w-4 h-4" /> Vehicle Arrived
               </div>
             )}
          </div>
        )}
      </div>
    </div>
  );
}
