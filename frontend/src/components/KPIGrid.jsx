import React from 'react';
import { Activity, Car, AlertTriangle, Clock, FastForward, CheckCircle } from 'lucide-react';

export default function KPIGrid({ metrics }) {
  if (!metrics) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 animate-pulse">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="panel h-20 bg-surfaceHover/50"></div>
        ))}
      </div>
    );
  }

  const kpis = [
    { label: 'Network Load', value: `${metrics.network_load_pct}%`, sub: 'Total capacity used', icon: Activity, color: 'text-primary' },
    { label: 'Active Vehicles', value: metrics.total_vehicles, sub: 'In monitored zones', icon: Car, color: 'text-text' },
    { label: 'Avg Congestion', value: `${metrics.avg_congestion_pct}%`, sub: 'Current network state', icon: AlertTriangle, color: 'text-warning' },
    { label: 'Congested Roads', value: metrics.total_congested_roads, sub: 'Ratio > 1.0', icon: AlertTriangle, color: metrics.total_congested_roads > 3 ? 'text-danger' : 'text-success' },
    { label: 'Avg Wait Time', value: `${metrics.avg_waiting_time_sec}s`, sub: 'Per signal approach', icon: Clock, color: 'text-muted' },
    { label: 'Avg Speed', value: `${metrics.avg_speed_kmh} km/h`, sub: 'Network average', icon: FastForward, color: 'text-primary' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
      {kpis.map((kpi, i) => (
        <div key={i} className="panel p-4 flex flex-col justify-center relative overflow-hidden group">
          <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <kpi.icon className="w-20 h-20" />
          </div>
          <div className="flex items-center gap-2 mb-1">
            <kpi.icon className={`w-4 h-4 ${kpi.color}`} />
            <span className="text-xs font-semibold text-muted tracking-wider uppercase">{kpi.label}</span>
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight">{kpi.value}</div>
          <div className="text-[10px] text-muted/80 mt-1">{kpi.sub}</div>
        </div>
      ))}
    </div>
  );
}
