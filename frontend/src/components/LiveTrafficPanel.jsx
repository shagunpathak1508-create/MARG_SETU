import React, { useState, useEffect } from 'react';
import { fetchTraffic } from '../api';
import { AlertCircle } from 'lucide-react';

export default function LiveTrafficPanel() {
  const [traffic, setTraffic] = useState([]);
  const [loading, setLoading] = useState(true);

  // Initial load
  useEffect(() => {
    fetchTraffic()
      .then(data => {
        setTraffic(data);
        setLoading(false);
      })
      .catch(console.error);
  }, []);

  // Simulate real-time fluctuation
  useEffect(() => {
    if (traffic.length === 0) return;
    const interval = setInterval(() => {
      setTraffic(prev => prev.map(seg => {
        // Only fluctuate unblocked roads slightly
        if (seg.blocked) return seg;
        const change = Math.floor(Math.random() * 5) - 2; // -2 to +2
        let newVehicles = Math.max(0, seg.vehicle_count + change);
        
        // Don't let it drift too far from capacity
        if (newVehicles > seg.capacity * 1.5) newVehicles -= 3;
        
        const newRatio = seg.capacity > 0 ? newVehicles / seg.capacity : 0;
        return {
          ...seg,
          vehicle_count: newVehicles,
          congestion_ratio: newRatio,
          congestion_status: newRatio > 1.0 ? "Congested" : (newRatio > 0.7 ? "Moderate" : "Normal")
        };
      }));
    }, 5000); // Every 5s
    return () => clearInterval(interval);
  }, [traffic.length]);

  if (loading) return <div className="animate-pulse flex space-y-4 flex-col"><div className="h-4 bg-border rounded w-1/4"></div><div className="h-10 bg-border rounded"></div><div className="h-10 bg-border rounded"></div></div>;

  return (
    <div className="w-full">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-xs uppercase tracking-wider text-muted border-b border-border">
            <th className="pb-2 font-medium">Road</th>
            <th className="pb-2 font-medium">From ➝ To</th>
            <th className="pb-2 font-medium text-right">Count</th>
            <th className="pb-2 font-medium text-right">Cap</th>
            <th className="pb-2 font-medium text-right">Load</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {traffic.map(t => {
            const ratio = t.congestion_ratio;
            let statusColor = "bg-success text-success border-success/30";
            let dot = "bg-success";
            if (t.blocked) {
              statusColor = "bg-danger text-danger border-danger/30";
              dot = "bg-danger";
            } else if (ratio > 1) {
              statusColor = "bg-danger text-danger border-danger/30";
              dot = "bg-danger";
            } else if (ratio > 0.7) {
              statusColor = "bg-warning text-warning border-warning/30";
              dot = "bg-warning";
            }

            return (
              <tr key={t.segment_id} className="border-b border-border/50 hover:bg-surfaceHover transition-colors">
                <td className="py-2.5 flex items-center gap-2">
                  {t.blocked && <AlertCircle className="w-4 h-4 text-danger" />}
                  <span className={`font-medium ${t.blocked ? 'text-danger line-through opacity-70' : ''}`}>{t.road}</span>
                </td>
                <td className="py-2.5 text-muted">{t.from_junction} ➝ {t.to_junction}</td>
                <td className="py-2.5 text-right font-mono transition-all duration-300">{t.vehicle_count}</td>
                <td className="py-2.5 text-right text-muted">{t.capacity}</td>
                <td className="py-2.5 text-right">
                  <span className={`font-mono ${ratio > 1 ? 'text-danger' : (ratio > 0.7 ? 'text-warning' : 'text-success')}`}>
                    {Math.round(ratio * 100)}%
                  </span>
                </td>
                <td className="py-2.5">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${dot} ${t.blocked ? 'animate-pulse' : ''}`}></span>
                    <span className={`text-xs font-semibold ${statusColor.split(' ')[1]}`}>
                      {t.blocked ? 'BLOCKED' : t.congestion_status}
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
