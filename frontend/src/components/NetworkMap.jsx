import React, { useState, useEffect, useRef } from 'react';
import { fetchJunctions, fetchTraffic } from '../api';

export default function NetworkMap() {
  const [junctions, setJunctions] = useState([]);
  const [segments, setSegments] = useState([]);
  
  // Coordinates mapping logic
  // Our data uses relative lats and lngs (e.g. 10 to 90). We need to map this to SVG coordinates (0-100%).
  
  useEffect(() => {
    Promise.all([fetchJunctions(), fetchTraffic()])
      .then(([jData, tData]) => {
        setJunctions(jData);
        setSegments(tData);
      })
      .catch(console.error);
  }, []);

  // Poll for traffic updates to update colors
  useEffect(() => {
    const interval = setInterval(() => {
      fetchTraffic().then(setSegments).catch(console.error);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!junctions.length || !segments.length) {
    return <div className="absolute inset-0 flex items-center justify-center text-muted">Initializing Neural Map...</div>;
  }

  // Find min/max to normalize coordinates to SVG space (with some padding)
  const lats = junctions.map(j => j.lat);
  const lngs = junctions.map(j => j.lng);
  const minLat = Math.min(...lats) - 10;
  const maxLat = Math.max(...lats) + 10;
  const minLng = Math.min(...lngs) - 10;
  const maxLng = Math.max(...lngs) + 10;

  const toX = (lng) => ((lng - minLng) / (maxLng - minLng)) * 100;
  // SVG y is top-down, so invert lat
  const toY = (lat) => (1 - ((lat - minLat) / (maxLat - minLat))) * 100;

  // Build a lookup for junctions by ID to draw edges
  const jMap = {};
  junctions.forEach(j => {
    jMap[j.junction_id] = { x: toX(j.lng), y: toY(j.lat), name: j.name };
  });

  return (
    <div className="absolute inset-0 overflow-hidden bg-[#05070a]">
      {/* Grid background effect */}
      <div className="absolute inset-0 opacity-[0.03] bg-[linear-gradient(to_right,#808080_1px,transparent_1px),linear-gradient(to_bottom,#808080_1px,transparent_1px)] bg-[size:40px_40px]"></div>
      
      <svg className="w-full h-full" style={{ filter: 'drop-shadow(0 0 4px rgba(0,0,0,0.5))' }}>
        
        {/* Draw Edges (Roads) */}
        {segments.map(seg => {
          const start = jMap[seg.from_junction];
          const end = jMap[seg.to_junction];
          if (!start || !end) return null;

          // Determine color based on congestion
          let stroke = '#22c55e'; // Success green
          let opacity = 0.6;
          if (seg.blocked) {
            stroke = '#ef4444'; // Red
            opacity = 0.8;
          } else if (seg.congestion_ratio > 1.0) {
            stroke = '#f43f5e'; // Rose
            opacity = 0.8;
          } else if (seg.congestion_ratio > 0.7) {
            stroke = '#f59e0b'; // Amber
            opacity = 0.8;
          }

          return (
            <g key={seg.segment_id}>
              {/* Outer glow line */}
              <line 
                x1={`${start.x}%`} y1={`${start.y}%`} 
                x2={`${end.x}%`} y2={`${end.y}%`} 
                stroke={stroke} 
                strokeWidth={seg.blocked ? 4 : (seg.congestion_ratio > 1 ? 3 : 2)} 
                opacity={opacity * 0.3}
                style={{ filter: 'blur(3px)' }}
              />
              {/* Core line */}
              <line 
                x1={`${start.x}%`} y1={`${start.y}%`} 
                x2={`${end.x}%`} y2={`${end.y}%`} 
                stroke={stroke} 
                strokeWidth={seg.blocked ? 2 : 1.5} 
                opacity={opacity}
                strokeDasharray={seg.blocked ? "4,4" : "none"}
                className={seg.blocked ? "animate-[pulse_2s_ease-in-out_infinite]" : "transition-colors duration-1000"}
              />
            </g>
          );
        })}

        {/* Draw Nodes (Junctions) */}
        {junctions.map(j => {
          const x = toX(j.lng);
          const y = toY(j.lat);
          return (
            <g key={j.junction_id} className="group cursor-pointer">
              <circle cx={`${x}%`} cy={`${y}%`} r="3" fill="#0f172a" stroke="#38bdf8" strokeWidth="1.5" className="group-hover:fill-primary transition-colors" />
              {/* Label */}
              <text 
                x={`${x}%`} y={`${y - 2}%`} 
                textAnchor="middle" 
                fill="#94a3b8" 
                fontSize="10"
                className="opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none drop-shadow-md"
              >
                {j.name} ({j.junction_id})
              </text>
            </g>
          );
        })}
      </svg>
      
      {/* Badge overlay */}
      <div className="absolute bottom-4 right-4 bg-background/80 border border-border px-3 py-1.5 rounded-lg text-xs font-mono text-muted backdrop-blur-sm flex items-center gap-2 shadow-xl">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        Neural Routing Engine Active
      </div>
    </div>
  );
}
