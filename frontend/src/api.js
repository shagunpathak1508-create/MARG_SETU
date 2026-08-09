const BASE_URL = import.meta.env.VITE_API_URL || '';

export async function fetchTraffic() {
  const res = await fetch(`${BASE_URL}/traffic`);
  if (!res.ok) throw new Error('Failed to fetch traffic');
  return res.json();
}

export async function fetchJunctions() {
  const res = await fetch(`${BASE_URL}/junctions`);
  if (!res.ok) throw new Error('Failed to fetch junctions');
  return res.json();
}

export async function fetchComparison() {
  const res = await fetch(`${BASE_URL}/api/analytics/comparison`);
  if (!res.ok) throw new Error('Failed to fetch comparison');
  return res.json();
}

export async function optimizeSignal(junctionId) {
  const res = await fetch(`${BASE_URL}/api/signals/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ junction_id: junctionId })
  });
  if (!res.ok) throw new Error('Failed to optimize signal');
  return res.json();
}

export async function activateSignal(junctionId) {
  const res = await fetch(`${BASE_URL}/api/signals/activate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ junction_id: junctionId })
  });
  if (!res.ok) throw new Error('Failed to activate signal');
  return res.json();
}

export async function fetchSignals(junctionId = null) {
  const url = junctionId ? `${BASE_URL}/api/signals?junction_id=${junctionId}` : `${BASE_URL}/api/signals`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch signals');
  return res.json();
}

export async function createEmergencyCorridor(data) {
  const res = await fetch(`${BASE_URL}/api/emergency/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to create corridor');
  }
  return res.json();
}

export async function activateEmergencyCorridor(corridorId) {
  const res = await fetch(`${BASE_URL}/api/emergency/${corridorId}/activate`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to activate corridor');
  return res.json();
}

export async function advanceEmergencyCorridor(corridorId) {
  const res = await fetch(`${BASE_URL}/api/emergency/${corridorId}/advance`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to advance corridor');
  return res.json();
}

export async function recommendDiversion(segmentId) {
  const res = await fetch(`${BASE_URL}/api/diversion/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blocked_segment: segmentId })
  });
  if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to recommend diversion');
  }
  return res.json();
}

export async function activateDiversion(diversionId) {
  const res = await fetch(`${BASE_URL}/api/diversion/activate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ diversion_id: diversionId })
  });
  if (!res.ok) throw new Error('Failed to activate diversion');
  return res.json();
}

export async function runSimulation(params) {
  const res = await fetch(`${BASE_URL}/api/simulation/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) throw new Error('Failed to run simulation');
  return res.json();
}
